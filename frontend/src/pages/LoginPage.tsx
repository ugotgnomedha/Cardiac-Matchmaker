import { Button, Card, Form } from "@heroui/react";
import { startTransition, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { FormFields, type FormFieldConfig } from "../components/FormFields";
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

  const loginFields: FormFieldConfig[] = [
    {
      autoComplete: "email",
      description: "Use the account email created for this workspace.",
      kind: "input",
      label: "Email address",
      name: "email",
      onChange: setEmail,
      placeholder: "researcher@example.com",
      required: true,
      type: "email",
      value: email,
    },
    {
      autoComplete: "current-password",
      description: "Enter the password for the selected research account.",
      kind: "input",
      label: "Password",
      name: "password",
      onChange: setPassword,
      placeholder: "Password",
      required: true,
      type: "password",
      value: password,
    },
  ];

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
    <main className="min-h-screen bg-white px-4 py-6 text-zinc-950 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-md gap-6">
        <Card className="rounded-lg border border-zinc-200 bg-white">
          <Card.Header className="space-y-3 px-6 pt-6 pb-0">
            <h1 className="text-2xl font-semibold tracking-normal">Login</h1>
          </Card.Header>

          <Card.Content className="px-6 py-6">
            <Form className="space-y-5" onSubmit={handleSubmit}>
              <FormFields fields={loginFields} />

              {errorMessage ? (
                <p
                  className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
                  role="alert"
                >
                  {errorMessage}
                </p>
              ) : null}

              <Button fullWidth isDisabled={isSubmitting} type="submit">
                {isSubmitting ? "Signing in..." : "Login"}
              </Button>
            </Form>
          </Card.Content>
        </Card>
      </div>
    </main>
  );
}
