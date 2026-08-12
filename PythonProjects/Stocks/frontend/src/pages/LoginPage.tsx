import { LoginForm } from '@/components/auth/LoginForm'

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Branding */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-foreground">StockIQ</h1>
          <p className="text-muted-foreground mt-2">AI-Powered Stock Analysis Platform</p>
        </div>
        {/* Card */}
        <div className="bg-card border border-border rounded-lg p-8 shadow-lg">
          <h2 className="text-xl font-semibold text-foreground mb-6">Sign in to your account</h2>
          <LoginForm />
        </div>
        <p className="text-center text-muted-foreground mt-4 text-sm">
          Don't have an account?{' '}
          <a href="/register" className="text-primary hover:underline">Create one</a>
        </p>
      </div>
    </div>
  )
}
