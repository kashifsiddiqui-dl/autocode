"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Activity, AlertCircle, Loader2 } from "lucide-react";
import { handleSSOCallback } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export default function CallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const errorParam = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (errorParam) {
      setError(errorDescription || errorParam);
      return;
    }

    if (!code) {
      setError("No authorization code received. Please try signing in again.");
      return;
    }

    handleSSOCallback(code)
      .then(() => {
        router.replace("/code");
      })
      .catch((err) => {
        setError(err.message || "Authentication failed. Please try again.");
      });
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-50 px-4 dark:bg-neutral-950">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
            <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
          </div>
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-white">
            Authentication Failed
          </h1>
          <p className="mt-2 max-w-sm text-sm text-neutral-500">{error}</p>
          <Button
            className="mt-4"
            variant="outline"
            onClick={() => router.push("/login")}
          >
            Back to Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <Activity className="mx-auto mb-4 h-8 w-8 text-primary-600" />
        <Loader2 className="mx-auto mb-2 h-6 w-6 animate-spin text-primary-600" />
        <p className="text-sm text-neutral-500">Completing sign in...</p>
      </div>
    </div>
  );
}
