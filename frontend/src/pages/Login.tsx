import { useEffect, useState } from "react";
import { Navigate, useNavigate, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "@/components/ui/toaster";
import { LocaleSwitch } from "@/components/LocaleSwitch";
import { api, apiError } from "@/lib/api";
import { deviceName, loadRemember, peekAuthNotice, saveAuth, saveRemember, useAuth } from "@/lib/auth";
import type { LoginResponse } from "@/types/api";
import crestUrl from "../../../packages/design-system/brand/crest-mark.png";

export default function Login() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const { isAuthenticated, setUser } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  // Sent here because the session ended (signed out on another device or by an
  // admin, a password change, or 30 days unused): say so above the form until the
  // next sign-in clears it. Inline, not a toast: on a fresh page load a mount-time
  // toast fires before the Toaster is listening and is lost.
  const [signedOut] = useState(() => peekAuthNotice() === "signedOut");

  useEffect(() => {
    const r = loadRemember();
    if (r?.identifier) {
      setIdentifier(r.identifier);
      setRemember(true);
    }
  }, []); // mount only: the remembered identifier is read once

  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post<LoginResponse>("/auth/login", {
        identifier: identifier.trim(),
        password,
        // With `remember` the server also sets the HttpOnly refresh cookie that
        // keeps this browser signed in for 30 days (refreshSession in lib/api.ts).
        remember,
        device: { name: deviceName(), platform: "web" },
      });
      const user = {
        role: data.role,
        name: data.name,
        allowed_classes: data.allowed_classes,
        allowed_menus: data.allowed_menus ?? [],
      };
      saveAuth(data.token, user);
      setUser(user);
      saveRemember(remember ? { identifier: identifier.trim() } : null);
      if (data.force_password_change) {
        toast(t("portal.login.mustChangePassword"), "warning");
      }
      nav("/dashboard", { replace: true });
    } catch (e) {
      toast(apiError(e), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative" style={{ background: "linear-gradient(135deg, var(--color-deep-indigo) 0%, var(--color-khalsa-blue) 100%)" }}>
      <div className="absolute top-4 right-4">
        <LocaleSwitch className="bg-white/95" />
      </div>
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-6">
          <img src={crestUrl} alt="" width="80" height="64" className="h-16 w-auto mx-auto mb-3" />
          <h1 className="font-display text-heading-md text-deep-indigo">{t("common.schoolNameShort")}</h1>
          <p className="crest-caps text-khalsa-blue mt-1">{t("common.lockup")}</p>
          <p className="text-sm text-muted-foreground mt-2">{t("portal.login.signIn")}</p>
        </div>
        {signedOut && (
          <div role="status" className="mb-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-700 mt-0.5 shrink-0" aria-hidden />
            <span>{t("portal.auth.signedOut", "Your session ended. Please sign in again.")}</span>
          </div>
        )}
        <form className="space-y-3" onSubmit={submit}>
          <div className="space-y-1.5">
            <Label>{t("portal.login.identifier")}</Label>
            <Input
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              autoComplete="username"
              placeholder={t("portal.login.identifierPlaceholder")}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label>{t("portal.login.password")}</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2">
              <Checkbox id="remember" className="mt-0.5" checked={remember} onCheckedChange={(v) => setRemember(!!v)} />
              <div className="space-y-0.5">
                <Label htmlFor="remember" className="cursor-pointer">{t("portal.login.rememberMe")}</Label>
                <p className="text-xs text-muted-foreground">
                  {t("portal.login.rememberHint", "Stay signed in on this browser for 30 days")}
                </p>
              </div>
            </div>
            <Link to="/forgot-password" className="text-sm font-medium text-khalsa-blue hover:underline shrink-0">
              {t("portal.login.forgotLink")}
            </Link>
          </div>
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? t("portal.login.submittingLabel") : t("portal.login.submit")}
          </Button>
        </form>
        <p className="mt-6 text-caption text-muted-foreground text-center">{t("portal.login.footer")}</p>
      </Card>
    </div>
  );
}
