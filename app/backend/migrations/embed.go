// Package migrations menyematkan berkas SQL skema ke dalam biner Go.
package migrations

import "embed"

//go:embed *.sql
var FS embed.FS