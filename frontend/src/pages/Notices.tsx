import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/utils";
import type { Notice } from "@/types/api";
import { useTranslation } from "react-i18next";

const PRIORITIES = ["normal", "medium", "high"] as const;
const AUDIENCES = ["all", "teachers", "parents"];

export default function Notices() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { isAdmin, user } = useAuth();
  const [filter, setFilter] = useState<string>("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [priority, setPriority] = useState<typeof PRIORITIES[number]>("normal");
  const [audience, setAudience] = useState("all");

  const noticesQ = useQuery<Notice[]>({
    queryKey: ["notices"],
    queryFn: () => api.get("/notices").then((r) => r.data),
  });
  useSSE("notices", [["notices"]]);

  const filtered = useMemo(
    () => (noticesQ.data ?? []).filter((n) => !filter || n.priority === filter),
    [noticesQ.data, filter]
  );

  const create = useMutation({
    mutationFn: () => api.post("/notices", { title, content, priority, audience }),
    onSuccess: () => {
      toast("Notice posted", "success");
      setTitle(""); setContent("");
      qc.invalidateQueries({ queryKey: ["notices"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const del = useMutation({
    mutationFn: (id: number) => api.delete(`/notices/${id}`),
    onSuccess: () => { toast("Notice deleted", "warning"); qc.invalidateQueries({ queryKey: ["notices"] }); },
    onError: (e) => toast(apiError(e), "error"),
  });

  const pBadge = (p: string) => p === "high" ? "destructive" : p === "medium" ? "warning" : "info";

  return (
    <div className="space-y-4">
      <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.notices")}</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Post a notice</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (!title || !content) return toast("Title and content required", "warning"); create.mutate(); }}>
              <div className="space-y-1.5"><Label>Title</Label><Input value={title} onChange={(e) => setTitle(e.target.value)} required /></div>
              <div className="space-y-1.5"><Label>Content</Label><Textarea rows={4} value={content} onChange={(e) => setContent(e.target.value)} required /></div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5"><Label>Priority</Label>
                  <Select value={priority} onValueChange={(v) => setPriority(v as typeof PRIORITIES[number])}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{PRIORITIES.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5"><Label>Audience</Label>
                  <Select value={audience} onValueChange={setAudience}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{AUDIENCES.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <Button type="submit" disabled={create.isPending}>{create.isPending ? "Posting…" : "Post notice"}</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center justify-between">
            <span>All notices</span>
            <Select value={filter || "__all"} onValueChange={(v) => setFilter(v === "__all" ? "" : v)}>
              <SelectTrigger className="w-32"><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">All</SelectItem>
                {PRIORITIES.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
              </SelectContent>
            </Select>
          </CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {filtered.map((n) => (
              <div key={n.id} className="border-l-4 pl-3 py-2 rounded-r"
                style={{ borderColor: n.priority === "high" ? "#ef4444" : n.priority === "medium" ? "#f59e0b" : "#0ea5e9", background: "#f8fafc" }}>
                <div className="flex justify-between items-start">
                  <div>
                    <b>{n.title}</b>
                    <Badge variant={pBadge(n.priority)} className="ml-2">{n.priority}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <small className="text-muted-foreground">{formatDate(n.created_at)}</small>
                    {isAdmin && (
                      <Button size="icon" variant="ghost" className="text-red-600" onClick={() => confirm("Delete notice?") && del.mutate(n.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mt-1">{n.content}</p>
                <small className="text-xs text-muted-foreground">Posted by {n.posted_by} · For {n.audience}</small>
              </div>
            ))}
            {!filtered.length && <p className="text-muted-foreground text-sm">No notices</p>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
