import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import { ApiError } from '@/lib/api'

// Backend'in döndürdüğü fields hatalarını forma işler.
// Forma bağlanamayan bir hata kalırsa genel mesajı döndürür, o da formun üstünde gösterilir.
export function applyApiErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fieldNames: readonly Path<T>[],
): string | null {
  if (!(error instanceof ApiError)) return 'Beklenmeyen bir hata oluştu.'

  let applied = false
  for (const [field, message] of Object.entries(error.fields ?? {})) {
    if ((fieldNames as readonly string[]).includes(field)) {
      setError(field as Path<T>, { message })
      applied = true
    }
  }
  return applied ? null : error.message
}
