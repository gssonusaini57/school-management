import { Smartphone, Download, Apple, CheckCircle2, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTranslation } from "react-i18next";

const ANDROID_APK_URL = `${import.meta.env.BASE_URL}downloads/kis-attendance.apk`;

export default function MobileApps() {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.mobileApps")}</h1>
        <p className="text-sm text-muted-foreground">
          Native apps for teachers to take attendance on their phones.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Android */}
        <Card>
          <CardHeader className="flex flex-row items-start justify-between space-y-0">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-lg bg-emerald-500/10 inline-flex items-center justify-center">
                <Smartphone className="h-6 w-6 text-emerald-600" />
              </div>
              <div>
                <CardTitle>Android</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">v1.0.0 · Direct APK</p>
              </div>
            </div>
            <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
              <CheckCircle2 className="h-3 w-3 mr-1" /> Available
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Install on Android 8+ phones. Sign in with your email (or phone) and password to take
              attendance for your assigned classes.
            </p>
            <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground space-y-1">
              <div className="font-semibold text-foreground">Install steps</div>
              <ol className="list-decimal pl-4 space-y-0.5">
                <li>Tap <span className="font-medium">Download APK</span> below.</li>
                <li>Open the file once it finishes downloading.</li>
                <li>If prompted, allow installation from this source.</li>
                <li>Open <span className="font-medium">KIS Attendance</span> and sign in.</li>
              </ol>
            </div>
            <Button asChild className="w-full">
              <a href={ANDROID_APK_URL} download>
                <Download className="h-4 w-4 mr-2" /> Download APK
              </a>
            </Button>
          </CardContent>
        </Card>

        {/* iOS */}
        <Card>
          <CardHeader className="flex flex-row items-start justify-between space-y-0">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-lg bg-slate-900/5 inline-flex items-center justify-center">
                <Apple className="h-6 w-6 text-slate-700" />
              </div>
              <div>
                <CardTitle>iOS</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">v1.0.0 · TestFlight</p>
              </div>
            </div>
            <Badge variant="outline" className="text-amber-700 border-amber-300">
              <Clock className="h-3 w-3 mr-1" /> Coming soon
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              The iOS app is built (SwiftUI). Distribution requires an Apple Developer account; teachers
              will receive a TestFlight invite by email once it is published.
            </p>
            <div className="rounded-md bg-muted/50 p-3 text-xs text-muted-foreground space-y-1">
              <div className="font-semibold text-foreground">Install steps (once invited)</div>
              <ol className="list-decimal pl-4 space-y-0.5">
                <li>Install <span className="font-medium">TestFlight</span> from the App Store.</li>
                <li>Open the invite email on your iPhone and tap <span className="font-medium">View in TestFlight</span>.</li>
                <li>Tap <span className="font-medium">Install</span>, then open KIS Attendance.</li>
                <li>Sign in with your email (or phone) and password.</li>
              </ol>
            </div>
            <Button className="w-full" disabled>
              TestFlight invite required
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="text-xs text-muted-foreground">
        Both apps connect to <code className="bg-muted px-1 py-0.5 rounded">{window.location.host}</code>.
        Teachers sign in with the same email/phone and password they use on the website.
      </div>
    </div>
  );
}
