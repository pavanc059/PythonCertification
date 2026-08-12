import { RegisterForm } from '@/components/auth/RegisterForm'

export default function RegisterPage() {
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
          <h2 className="text-xl font-semibold text-foreground mb-6">Create your account</h2>
          <RegisterForm />
        </div>
        <p className="text-center text-muted-foreground mt-4 text-sm">
          Already have an account?{' '}
          <a href="/login" className="text-primary hover:underline">Sign in</a>
        </p>
      </div>
    </div>
  )
}
