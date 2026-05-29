import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { toast } from "@/components/ui/toaster";
import { LocaleSwitch } from "@/components/LocaleSwitch";
import { api, apiError } from "@/lib/api";
import crestUrl from "../../../packages/design-system/brand/crest-mark.png";

export default function ResetPassword() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const token = useMemo(() => params.get("token") ?? "", [params]);

  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      toast(t("portal.reset.missingToken"), "error");
      return;
    }
    if (pw.length < 6) {
      toast(t("portal.reset.tooShort"), "error");
      return;
    }
    if (pw !== confirm) {
      toast(t("portal.reset.mismatch"), "error");
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw });
      setDone(true);
    } catch (e) {
      // Backend returns 400 for invalid/expired tokens.
      toast(apiError(e) || t("portal.reset.invalidLink"), "error");
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
          <h1 className="font-display text-heading-md text-deep-indigo">{t("portal.reset.title")}</h1>
          <p className="text-sm text-muted-foreground mt-2">{t("portal.reset.subtitle")}</p>
        </div>

        {done ? (
          <div className="space-y-4 text-center">
            <div className="rounded-lg bg-accent p-4 text-sm text-accent-foreground">
              <p className="font-semibold mb-1">{t("portal.reset.successTitle")}</p>
              <p>{t("portal.reset.successBody")}</p>
            </div>
            <Button className="w-full" onClick={() => nav("/login", { replace: true })}>
              {t("portal.reset.goToLogin")}
            </Button>
          </div>
        ) : !token ? (
          <div className="space-y-4 text-center">
            <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
              {t("portal.reset.invalidLink")}
            </div>
            <Link to="/forgot-password" className="inline-block text-sm font-medium text-khalsa-blue hover:underline">
              {t("portal.forgot.title")}
            </Link>
          </div>
        ) : (
          <form className="space-y-3" onSubmit={submit}>
            <div className="space-y-1.5">
              <Label>{t("portal.reset.newPassword")}</Label>
              <Input
                type="password"
                value={pw}
                onChange={(e) => setPw(e.target.value)}
                autoComplete="new-password"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>{t("portal.reset.confirmPassword")}</Label>
              <Input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? t("portal.reset.submitting") : t("portal.reset.submit")}
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
