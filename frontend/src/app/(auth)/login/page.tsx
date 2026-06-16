"use client";

import { useState } from "react";
import { Activity, ArrowRight, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { redirectToSSO } from "@/lib/auth";

export default function LoginPage() {
  const [tenantSlug, setTenantSlug] = useState("");
  const [isRedirecting, setIsRedirecting] = useState(false);

  const handleLogin = () => {
    if (!tenantSlug.trim()) return;
    setIsRedirecting(true);
    redirectToSSO(tenantSlug.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleLogin();
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-50 via-white to-clinical-50 px-4 dark:from-neutral-950 dark:via-neutral-900 dark:to-neutral-950">
      <div className="w-full max-w-md">
        {/* Logo and branding */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-600 to-clinical-600 shadow-lg">
            <Activity className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-neutral-900 dark:text-white">
            Auto Code
          </h1>
          <p className="mt-1 text-neutral-500">
            AI-Powered Medical Coding Assistant
          </p>
        </div>

        {/* Login card */}
        <Card className="shadow-lg">
          <CardHeader className="pb-4 text-center">
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">
              Sign in to your account
            </h2>
            <p className="text-sm text-neutral-500">
              Enter your organization to continue
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Tenant slug */}
            <div>
              <label
                htmlFor="tenant"
                className="mb-1.5 block text-sm font-medium text-neutral-700 dark:text-neutral-300"
              >
                Organization
              </label>
              <div className="flex items-center gap-2">
                <Input
                  id="tenant"
                  type="text"
                  placeholder="your-organization"
                  value={tenantSlug}
                  onChange={(e) => setTenantSlug(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="flex-1"
                  autoFocus
                />
                <span className="text-sm text-neutral-400">.autocode.app</span>
              </div>
            </div>

            {/* SSO Button */}
            <Button
              className="w-full gap-2"
              size="lg"
              onClick={handleLogin}
              disabled={!tenantSlug.trim() || isRedirecting}
            >
              <Shield className="h-4 w-4" />
              Sign in with Microsoft
              <ArrowRight className="h-4 w-4" />
            </Button>

            {/* Info text */}
            <p className="text-center text-xs text-neutral-400">
              Authentication is handled securely via your organization&apos;s Azure
              Active Directory. No passwords are stored by Auto Code.
            </p>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-neutral-400">
          HIPAA Compliant. SOC 2 Type II Certified.
        </p>
      </div>
    </div>
  );
}
