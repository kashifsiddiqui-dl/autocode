"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Save, Settings, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { toast } from "@/components/ui/toast";
import { getCurrentUser, isAuthenticated } from "@/lib/auth";
import type { CodingStandard } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const user = getCurrentUser();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  const [defaultStandard, setDefaultStandard] = useState<CodingStandard>("icd10cm");
  const [defaultProvider, setDefaultProvider] = useState("anthropic");
  const [maxResults, setMaxResults] = useState("10");
  const [minConfidence, setMinConfidence] = useState("0.3");

  const handleSave = () => {
    toast({
      title: "Settings saved",
      description: "Your preferences have been updated.",
      variant: "success",
    });
  };

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <div className="mx-auto max-w-3xl px-4 py-6 lg:px-8">
        <Button
          variant="ghost"
          size="sm"
          className="mb-4 -ml-2"
          onClick={() => router.back()}
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back
        </Button>

        <div className="mb-6">
          <h1 className="flex items-center gap-2 text-2xl font-bold text-neutral-900 dark:text-white">
            <Settings className="h-6 w-6 text-primary-600" />
            Settings
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Configure your Auto Code preferences and tenant settings.
          </p>
        </div>

        <div className="space-y-6">
          {/* Coding preferences */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Coding Preferences</CardTitle>
              <CardDescription>
                Configure default options for new coding sessions.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    Default Coding Standard
                  </label>
                  <Select value={defaultStandard} onValueChange={(v) => setDefaultStandard(v as CodingStandard)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="icd10cm">ICD-10-CM</SelectItem>
                      <SelectItem value="icd10pcs">ICD-10-PCS</SelectItem>
                      <SelectItem value="cpt">CPT</SelectItem>
                      <SelectItem value="hcpcs">HCPCS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    Default AI Provider
                  </label>
                  <Select value={defaultProvider} onValueChange={setDefaultProvider}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="anthropic">Claude (Anthropic)</SelectItem>
                      <SelectItem value="openai">GPT (OpenAI)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    Max Results Per Analysis
                  </label>
                  <Input
                    type="number"
                    min="1"
                    max="25"
                    value={maxResults}
                    onChange={(e) => setMaxResults(e.target.value)}
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    Minimum Confidence Threshold
                  </label>
                  <Input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={minConfidence}
                    onChange={(e) => setMinConfidence(e.target.value)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* SSO Configuration (admin only) */}
          {user?.role === "admin" && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Shield className="h-4 w-4 text-primary-600" />
                  SSO Configuration
                </CardTitle>
                <CardDescription>
                  Azure Active Directory integration settings. Contact support to
                  modify these values.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    Azure AD Tenant ID
                  </label>
                  <Input
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    disabled
                    className="bg-neutral-50 dark:bg-neutral-800"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium">
                    Client ID
                  </label>
                  <Input
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    disabled
                    className="bg-neutral-50 dark:bg-neutral-800"
                  />
                </div>
                <p className="text-xs text-neutral-400">
                  SSO configuration is managed at the tenant level. Contact your
                  administrator to make changes.
                </p>
              </CardContent>
            </Card>
          )}

          {/* Save */}
          <div className="flex justify-end">
            <Button onClick={handleSave} className="gap-2">
              <Save className="h-4 w-4" />
              Save Settings
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
