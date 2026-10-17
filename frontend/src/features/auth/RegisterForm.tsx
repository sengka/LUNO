import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { z } from 'zod'
import { CircleAlertIcon, Loader2Icon } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { FormField } from '@/components/form/FormField'
import { PasswordInput } from '@/components/form/PasswordInput'
import { ApiError } from '@/lib/api'
import { applyApiErrors } from '@/lib/form-errors'
import { authApi } from './api'

// Kurallar sözleşme 3.1'deki ile aynı (FR-004)
const registerSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(2, { error: 'Ad soyad en az 2 karakter olmalıdır.' })
    .max(100, { error: 'Ad soyad en fazla 100 karakter olabilir.' }),
  email: z.email({ error: 'Geçerli bir e-posta adresi gir.' }),
  password: z.string().min(8, { error: 'Şifre en az 8 karakter olmalıdır.' }),
})

type RegisterValues = z.infer<typeof registerSchema>

export function RegisterForm({ onRegistered }: { onRegistered: (email: string) => void }) {
  const [formError, setFormError] = useState<string | null>(null)

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { full_name: '', email: '', password: '' },
  })
  const { errors } = form.formState

  const register = useMutation({
    mutationFn: authApi.register,
    onSuccess: (user) => {
      // FR-002: "Kayıt başarılı" mesajı ve giriş sayfasına yönlendirme
      toast.success('Kayıt başarılı! Şimdi giriş yapabilirsin.')
      onRegistered(user.email)
    },
    onError: (error) => {
      // 409 EMAIL_ALREADY_EXISTS e-posta alanının altında gösterilir (FR-003)
      if (error instanceof ApiError && error.code === 'EMAIL_ALREADY_EXISTS') {
        form.setError('email', { message: error.message })
        return
      }
      setFormError(applyApiErrors(error, form.setError, ['full_name', 'email', 'password']))
    },
  })

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null)
    register.mutate(values)
  })

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5">
      <div className="grid gap-1">
        <h2 className="text-2xl font-semibold text-brand">LUNO'ya katıl</h2>
        <p className="text-sm text-muted-foreground">Hesabını oluştur, ilk projen için adım at.</p>
      </div>

      <FormField id="register-name" label="Ad soyad" error={errors.full_name?.message}>
        <Input
          id="register-name"
          autoComplete="name"
          placeholder="Ayşe Yılmaz"
          aria-invalid={!!errors.full_name}
          {...form.register('full_name')}
        />
      </FormField>

      <FormField id="register-email" label="E-posta" error={errors.email?.message}>
        <Input
          id="register-email"
          type="email"
          autoComplete="email"
          placeholder="ornek@mail.com"
          aria-invalid={!!errors.email}
          {...form.register('email')}
        />
      </FormField>

      <FormField
        id="register-password"
        label="Şifre"
        error={errors.password?.message}
        hint="En az 8 karakter"
      >
        <PasswordInput
          id="register-password"
          autoComplete="new-password"
          aria-invalid={!!errors.password}
          {...form.register('password')}
        />
      </FormField>

      <Button type="submit" size="lg" disabled={register.isPending}>
        {register.isPending && <Loader2Icon className="animate-spin" />}
        Kayıt ol
      </Button>

      {formError && (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}
    </form>
  )
}
