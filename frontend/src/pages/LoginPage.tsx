import { Button, Card, Input } from "@heroui/react";
import { startTransition, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { isApiError } from "../utils/api";

type LoginLocationState = {
  from?: string;
};

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const redirectTo = (location.state as LoginLocationState | null)?.from ?? "/";

  if (user) {
    return <Navigate to={redirectTo} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login({ email, password });

      startTransition(() => {
        navigate(redirectTo, { replace: true });
      });
    } catch (error) {
      if (isApiError(error)) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to sign in right now.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="rounded-[2rem] border backdrop-blur-xl">
          <Card.Header className="space-y-3 px-8 pt-8 pb-0 sm:px-10 sm:pt-10">
            Login
          </Card.Header>

          <Card.Content className="px-8 py-8 sm:px-10 sm:py-10">
            <form className="space-y-5" onSubmit={handleSubmit}>
              <label className="block space-y-2 text-sm font-medium text-stone-700">
                <span>Email</span>
                <Input
                  autoComplete="email"
                  fullWidth
                  name="email"
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  type="email"
                  value={email}
                />
              </label>

              <label className="block space-y-2 text-sm font-medium text-stone-700">
                <span>Password</span>
                <Input
                  autoComplete="current-password"
                  fullWidth
                  name="password"
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
              </label>

              {errorMessage ? (
                <p
                  className="rounded-2xl border px-4 py-3 text-sm text-rose-700"
                  role="alert"
                >
                  {errorMessage}
                </p>
              ) : null}

              <Button fullWidth isDisabled={isSubmitting} type="submit">
                {isSubmitting ? "Signing in..." : "Login"}
              </Button>
            </form>
          </Card.Content>
        </Card>
      </div>
    </main>
  );
}
