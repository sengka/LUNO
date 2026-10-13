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
import { applyApiErrors } from '@/lib/form-errors'
import { authApi } from './api'
import { useAuth } from './auth-context'

const loginSchema = z.object({
  email: z.email({ error: 'Geçerli bir e-posta adresi gir.' }),
  password: z.string().min(1, { error: 'Şifre zorunludur.' }),
})

type LoginValues = z.infer<typeof loginSchema>

export function LoginForm({ defaultEmail = '' }: { defaultEmail?: string }) {
  const { signIn } = useAuth()
  const [formError, setFormError] = useState<string | null>(null)

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: defaultEmail, password: '' },
  })
  const { errors } = form.formState

  const login = useMutation({
    mutationFn: authApi.login,
    // Başarılı girişte GuestRoute kullanıcıyı uygulamaya yönlendirir
    onSuccess: signIn,
    onError: (error) => {
      // Hatalı e-posta/şifre (401 INVALID_CREDENTIALS) wireframe'deki kırmızı kutuda gösterilir
      setFormError(applyApiErrors(error, form.setError, ['email', 'password']))
    },
  })

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null)
    login.mutate(values)
  })

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5">
      <div className="grid gap-1">
        <h2 className="text-2xl font-semibold text-brand">Tekrar hoş geldin</h2>
        <p className="text-sm text-muted-foreground">Projelerine kaldığın yerden devam et.</p>
      </div>

      <FormField id="login-email" label="E-posta" error={errors.email?.message}>
        <Input
          id="login-email"
          type="email"
          autoComplete="email"
          placeholder="ornek@mail.com"
          aria-invalid={!!errors.email}
          {...form.register('email')}
        />
      </FormField>

      <FormField id="login-password" label="Şifre" error={errors.password?.message}>
        <PasswordInput
          id="login-password"
          autoComplete="current-password"
          aria-invalid={!!errors.password}
          {...form.register('password')}
        />
      </FormField>

      <Button type="submit" size="lg" disabled={login.isPending}>
        {login.isPending && <Loader2Icon className="animate-spin" />}
        Giriş yap
      </Button>

      {/* Şifre sıfırlama Sprint 8'de (US-027) gelecek */}
      <Button
        type="button"
        variant="link"
        className="h-auto justify-self-center p-0"
        onClick={() => toast.info('Şifre sıfırlama yakında eklenecek.')}
      >
        Şifremi unuttum
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
