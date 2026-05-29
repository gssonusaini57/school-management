import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { toast } from "@/components/ui/toaster";
import { LocaleSwitch } from "@/components/LocaleSwitch";
import { api, apiError } from "@/lib/api";
import crestUrl from "../../../packages/design-system/brand/crest-mark.png";

// Mirror of backend settings.RESET_TOKEN_TTL_MINUTES (display only).
const RESET_TTL_MINUTES = 30;

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      // Endpoint always returns a generic success — never reveals whether the
      // email exists, so we just flip to the "check your email" state.
      await api.post("/auth/forgot-password", { email: email.trim() });
      setSent(true);
    } catch (e) {
      toast(apiError(e), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 relative"
      style={{ background: "linear-gradient(135deg, var(--color-deep-indigo) 0%, var(--color-khalsa-blue) 100%)" }}
    >
      <div className="absolute top-4 right-4">
        <LocaleSwitch className="bg-white/95" />
      </div>
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-6">
          <img src={crestUrl} alt="" width="80" height="64" className="h-16 w-auto mx-auto mb-3" />
          <h1 className="font-display text-heading-md text-deep-indigo">{t("portal.forgot.title")}</h1>
          <p className="text-sm text-muted-foreground mt-2">{t("portal.forgot.subtitle")}</p>
        </div>

        {sent ? (
          <div className="space-y-4 text-center">
            <div className="rounded-lg bg-accent p-4 text-sm text-accent-foreground">
              <p className="font-semibold mb-1">{t("portal.forgot.sentTitle")}</p>
              <p>{t("portal.forgot.sentBody", { minutes: RESET_TTL_MINUTES })}</p>
            </div>
            <Link to="/login" className="inline-block text-sm font-medium text-khalsa-blue hover:underline">
              {t("portal.forgot.backToLogin")}
            </Link>
          </div>
        ) : (
          <form className="space-y-3" onSubmit={submit}>
            <div className="space-y-1.5">
              <Label>{t("portal.forgot.email")}</Label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                placeholder={t("portal.forgot.emailPlaceholder")}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? t("portal.forgot.submitting") : t("portal.forgot.submit")}
            </Button>
            <div className="text-center pt-1">
              <Link to="/login" className="text-sm font-medium text-khalsa-blue hover:underline">
                {t("portal.forgot.backToLogin")}
              </Link>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
