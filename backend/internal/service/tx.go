package service

import (
	"context"

	"harga-pangan-medan/backend/internal/repository"
)

// pgxTx adalah bagian dari pgx.Tx yang dibutuhkan service.
type pgxTx interface {
	repository.DBTX
	Commit(ctx context.Context) error
}