import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Logo } from '@/components/Logo'
import { LoginForm } from './LoginForm'
import { RegisterForm } from './RegisterForm'

type AuthTab = 'giris' | 'kayit'

// Wireframe: docs/tasarim/01-giris-kayit.png
export function AuthPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [registeredEmail, setRegisteredEmail] = useState('')

  const tab: AuthTab = location.pathname === '/kayit' ? 'kayit' : 'giris'

  // Sekme adresle aynı kalsın: /giris ve /kayit. Geldiği sayfa bilgisi (state) korunur.
  const changeTab = (value: string) => {
    navigate(`/${value}`, { replace: true, state: location.state })
  }

  const handleRegistered = (email: string) => {
    setRegisteredEmail(email)
    changeTab('giris')
  }

  return (
    <div className="grid min-h-svh lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <BrandPanel />

      <main className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <Logo className="mb-8 lg:hidden" />

          <Tabs value={tab} onValueChange={changeTab} className="gap-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="giris">Giriş yap</TabsTrigger>
              <TabsTrigger value="kayit">Kayıt ol</TabsTrigger>
            </TabsList>

            <Card>
              <CardContent>
                <TabsContent value="giris">
                  {/* key: kayıttan sonra e-posta alanı yeni değerle dolsun */}
                  <LoginForm key={registeredEmail} defaultEmail={registeredEmail} />
                </TabsContent>
                <TabsContent value="kayit">
                  <RegisterForm onRegistered={handleRegistered} />
                </TabsContent>
              </CardContent>
            </Card>
          </Tabs>
        </div>
      </main>
    </div>
  )
}

function BrandPanel() {
  return (
    <aside className="relative hidden overflow-hidden bg-secondary p-12 lg:flex lg:flex-col">
      {/* Wireframe'deki dekoratif şekiller */}
      <div className="absolute -top-24 right-[-6rem] size-96 rounded-full border-[3.5rem] border-primary/10" />
      <div className="absolute bottom-48 right-24 size-24 rounded-full bg-primary/20" />
      <div className="absolute -bottom-24 -left-16 h-80 w-[28rem] rounded-full bg-primary/25" />
      <div className="absolute -bottom-10 left-24 h-96 w-52 rotate-[30deg] rounded-full bg-primary/40" />

      <Logo className="relative" />

      <div className="relative my-auto max-w-md">
        <h1 className="text-5xl leading-tight font-bold text-brand">
          Projelerini baştan sona tek yerde yönet
        </h1>
        <p className="mt-6 text-lg text-muted-foreground">
          Planlarını netleştir, ekibinle birlikte ilerle. Her adımda, her projede LUNO yanında.
        </p>
      </div>

      <p className="relative text-sm font-medium text-brand">Daha düzenli projeler. Daha güçlü ekipler.</p>
    </aside>
  )
}
