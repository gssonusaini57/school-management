import * as React from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from "lucide-react";

type ToastKind = "success" | "error" | "warning" | "info";

interface ToastItem {
  id: number;
  msg: string;
  kind: ToastKind;
}

let push: ((m: string, k?: ToastKind) => void) | null = null;

export function toast(msg: string, kind: ToastKind = "success") {
  push?.(msg, kind);
}

export function Toaster() {
  const [items, setItems] = React.useState<ToastItem[]>([]);

  React.useEffect(() => {
    push = (msg, kind = "success") => {
      const id = Date.now() + Math.random();
      setItems((s) => [...s, { id, msg, kind }]);
      setTimeout(() => setItems((s) => s.filter((x) => x.id !== id)), 4000);
    };
    return () => { push = null; };
  }, []);

  const icons: Record<ToastKind, React.ReactNode> = {
    success: <CheckCircle2 className="h-5 w-5 text-emerald-600" />,
    error: <AlertCircle className="h-5 w-5 text-red-600" />,
    warning: <AlertTriangle className="h-5 w-5 text-amber-600" />,
    info: <Info className="h-5 w-5 text-sky-600" />,
  };
  const borders: Record<ToastKind, string> = {
    success: "border-l-emerald-600",
    error: "border-l-red-600",
    warning: "border-l-amber-600",
    info: "border-l-sky-600",
  };

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {items.map((t) => (
        <div
          key={t.id}
          className={cn(
            "flex items-center gap-3 bg-white shadow-lg rounded-md py-3 px-4 border-l-4 text-sm animate-in slide-in-from-right",
            borders[t.kind]
          )}
        >
          {icons[t.kind]}
          <span className="flex-1 text-foreground">{t.msg}</span>
          <button
            className="text-muted-foreground hover:text-foreground"
            onClick={() => setItems((s) => s.filter((x) => x.id !== t.id))}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
