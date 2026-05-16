import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend,
} from "chart.js";
import { Users, Briefcase, Wallet, ClipboardCheck, Megaphone } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useSSE } from "@/lib/sse";
import { CLASSES, COLORS, formatCurrency, formatDate } from "@/lib/utils";
import type { Student, Staff, FeePayment, Notice, AttendanceSummary } from "@/types/api";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const { isAdmin, user } = useAuth();
  const allowed = user?.allowed_classes ?? [];

  const students = useQuery<Student[]>({
    queryKey: ["students"],
    queryFn: () => api.get("/students", { params: { page_size: 1000 } }).then((r) => r.data.items),
  });
  const staff = useQuery<Staff[]>({ queryKey: ["staff"], queryFn: () => api.get("/staff").then((r) => r.data), enabled: isAdmin });
  const fees = useQuery<FeePayment[]>({ queryKey: ["fees"], queryFn: () => api.get("/fees").then((r) => r.data), enabled: isAdmin });
  const notices = useQuery<Notice[]>({ queryKey: ["notices"], queryFn: () => api.get("/notices").then((r) => r.data) });
  const attSummary = useQuery<AttendanceSummary>({ queryKey: ["attendance", "today"], queryFn: () => api.get("/attendance/today-summary").then((r) => r.data) });

  useSSE("dashboard", [["students"], ["staff"], ["fees"], ["notices"], ["attendance", "today"]]);

  const list = students.data ?? [];
  const studentCount = list.filter((s) => allowed.length === 0 || allowed.includes(s.class_name) || isAdmin).length;

  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const monthFee = (fees.data ?? []).reduce((sum, f) => {
    const d = new Date(f.date);
    return d >= monthStart && d <= now ? sum + Number(f.amount) : sum;
  }, 0);
  const monthLabel = now.toLocaleString(i18n.language === "pa" ? "pa-IN" : "en-IN", { month: "short" });

  const chartClasses = isAdmin ? CLASSES : allowed;
  const counts: Record<string, number> = {};
  chartClasses.forEach((c) => (counts[c] = 0));
  list.forEach((s) => { if (counts[s.class_name] !== undefined) counts[s.class_name]++; });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.dashboard.title")}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t("portal.dashboard.subtitle")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={<Users className="h-5 w-5" />} label={t("portal.dashboard.kpiStudents")} value={studentCount} bg="bg-khalsa-blue" />
        {isAdmin && (
          <StatCard icon={<Briefcase className="h-5 w-5" />} label={t("portal.nav.staff")} value={staff.data?.length ?? 0} bg="bg-success" />
        )}
        <StatCard
          icon={<ClipboardCheck className="h-5 w-5" />}
          label={t("portal.dashboard.kpiPresentToday")}
          value={
            attSummary.isLoading
              ? "…"
              : attSummary.data && attSummary.data.total
              ? `${attSummary.data.percent}%`
              : "—"
          }
          subtitle={
            attSummary.data && attSummary.data.total
              ? `${attSummary.data.present}/${attSummary.data.total}`
              : undefined
          }
          bg="bg-warning"
        />
        {isAdmin && (
          <StatCard
            icon={<Wallet className="h-5 w-5" />}
            label={`${t("portal.dashboard.kpiFeesCollected")} · ${monthLabel}`}
            value={monthFee >= 1000 ? (monthFee / 1000).toFixed(1) + "k" : monthFee.toString()}
            subtitle={formatCurrency(monthFee)}
            bg="bg-deep-indigo"
          />
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="font-display text-deep-indigo">{t("portal.dashboard.kpiStudents")}</CardTitle></CardHeader>
          <CardContent>
            <Bar
              data={{
                labels: chartClasses,
                datasets: [{ label: t("portal.dashboard.kpiStudents"), data: chartClasses.map((c) => counts[c] ?? 0), backgroundColor: COLORS, borderRadius: 6 }],
              }}
              options={{ responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-display text-deep-indigo">
              <Megaphone className="h-4 w-4" /> {t("portal.dashboard.recentNotices")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(notices.data ?? []).slice(0, 5).map((n) => (
              <div key={n.id} className="border-l-4 border-khalsa-blue pl-3 py-2 mb-2">
                <div className="flex justify-between items-start">
                  <b className="text-sm">{n.title}</b>
                  <Badge variant={n.priority === "high" ? "destructive" : n.priority === "medium" ? "warning" : "info"}>{n.priority}</Badge>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2">{n.content}</p>
                <span className="text-[10px] text-muted-foreground">{formatDate(n.created_at)}</span>
              </div>
            ))}
            {!notices.data?.length && <p className="text-sm text-muted-foreground">{t("portal.common.noData")}</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, subtitle, bg }: { icon: React.ReactNode; label: string; value: string | number; subtitle?: string; bg: string }) {
  return (
    <Card className={`${bg} text-white border-0`}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="bg-white/20 rounded-md p-2">{icon}</div>
        </div>
        <div className="font-display text-3xl font-bold mt-3">{value}</div>
        <div className="text-sm opacity-90">{label}</div>
        {subtitle && <div className="text-xs opacity-80 mt-0.5">{subtitle}</div>}
      </CardContent>
    </Card>
  );
}
