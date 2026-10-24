package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/pgx/v5"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/jackc/pgx/v5/pgxpool"

	"harga-pangan-medan/backend/internal/config"
	"harga-pangan-medan/backend/internal/handler"
	"harga-pangan-medan/backend/internal/repository"
	"harga-pangan-medan/backend/internal/service"
	"harga-pangan-medan/backend/migrations"
)

func main() {
	cfg := config.Load()

	ref, err := config.LoadReferensi(cfg.ReferensiPath)
	if err != nil {
		log.Fatalf("referensi: %v", err)
	}
	log.Printf("referensi dimuat (%s): %d kecamatan, %d komoditas, %d pasar, APP_ENV=%s",
		ref.StatusKonfigurasi, len(ref.Kecamatan), len(ref.Komoditas), len(ref.Pasar), cfg.AppEnv)

	if err := jalankanMigrasi(cfg.DatabaseURL); err != nil {
		log.Fatalf("migrasi: %v", err)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		log.Fatalf("koneksi database: %v", err)
	}
	defer pool.Close()

	repo := repository.New(pool)
	svc := service.New(repo, ref, cfg)
	h := handler.New(svc, cfg)

	srv := &http.Server{
		Addr:              ":" + cfg.Port,
		Handler:           h.Router(),
		ReadHeaderTimeout: 10 * time.Second,
	}
	go func() {
		log.Printf("API mendengarkan di :%s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("server: %v", err)
		}
	}()

	<-ctx.Done()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(shutdownCtx)
}

// jalankanMigrasi menunggu database siap (maks ~60 detik) lalu menerapkan migrasi yang tertanam.
func jalankanMigrasi(dsn string) error {
	src, err := iofs.New(migrations.FS, ".")
	if err != nil {
		return err
	}
	url := strings.Replace(strings.Replace(dsn, "postgresql://", "pgx5://", 1), "postgres://", "pgx5://", 1)

	var m *migrate.Migrate
	for i := 0; i < 30; i++ {
		m, err = migrate.NewWithSourceInstance("iofs", src, url)
		if err == nil {
			break
		}
		log.Printf("menunggu database (%d/30): %v", i+1, err)
		time.Sleep(2 * time.Second)
		if i < 29 {
			src, _ = iofs.New(migrations.FS, ".")
		}
	}
	if err != nil {
		return err
	}
	defer m.Close()
	if err := m.Up(); err != nil && !errors.Is(err, migrate.ErrNoChange) {
		return err
	}
	log.Println("skema database siap")
	return nil
}

var _ = os.Getenv
