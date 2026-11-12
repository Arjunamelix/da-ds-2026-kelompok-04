FROM golang:1.25-alpine AS build
# Izinkan Go mengunduh toolchain yang dibutuhkan go.mod (mis. 1.25.x terbaru) bila lebih baru dari image.
ENV GOTOOLCHAIN=auto
WORKDIR /src
COPY . .
# Bila go.sum belum di-commit, `go mod tidy` melengkapinya saat build.
# Sebaiknya jalankan `go mod tidy` sekali di laptop lalu commit go.mod dan go.sum.
RUN go mod tidy && CGO_ENABLED=0 go build -o /out/server ./cmd/server

FROM alpine:3.20
RUN adduser -D -u 10001 app
USER app
WORKDIR /app
COPY --from=build /out/server /app/server
EXPOSE 8080
CMD ["/app/server"]
