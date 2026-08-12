import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { loginUser } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
})

type LoginFormValues = z.infer<typeof loginSchema>

export function LoginForm() {
  const [serverError, setServerError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const setAuth = useAuthStore((s) => s.setAuth)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { rememberMe: false },
  })

  const onSubmit = async (data: LoginFormValues) => {
    setIsLoading(true)
    setServerError(null)
    try {
      const response = await loginUser({ email: data.email, password: data.password })
      setAuth(response.user, response.access_token)
      const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/dashboard'
      navigate(from, { replace: true })
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } }
      const msg = axiosErr.response?.data?.detail || 'Invalid email or password'
      setServerError(typeof msg === 'string' ? msg : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {serverError && (
        <div className="bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded p-3">
          {serverError}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-foreground mb-1">Email</label>
        <input
          type="email"
          {...register('email')}
          className="w-full px-3 py-2 bg-input border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm"
          placeholder="you@example.com"
        />
        {errors.email && (
          <p className="text-destructive text-xs mt-1">{errors.email.message}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-foreground mb-1">Password</label>
        <input
          type="password"
          {...register('password')}
          className="w-full px-3 py-2 bg-input border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring text-sm"
          placeholder="••••••••"
        />
        {errors.password && (
          <p className="text-destructive text-xs mt-1">{errors.password.message}</p>
        )}
      </div>

      <div className="flex items-center">
        <input
          type="checkbox"
          id="rememberMe"
          {...register('rememberMe')}
          className="mr-2"
        />
        <label htmlFor="rememberMe" className="text-sm text-muted-foreground">
          Remember me
        </label>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-2 px-4 bg-primary text-primary-foreground font-medium rounded-md hover:opacity-90 disabled:opacity-50 transition-opacity text-sm"
      >
        {isLoading ? 'Signing in...' : 'Sign in'}
      </button>
    </form>
  )
}
