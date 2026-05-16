import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Spinner({ className, full = false }: { className?: string; full?: boolean }) {
  if (full) {
    return (
      <div className="fixed inset-0 z-[80] bg-black/30 flex items-center justify-center">
        <Loader2 className={cn("h-8 w-8 animate-spin text-white", className)} />
      </div>
    );
  }
  return <Loader2 className={cn("h-4 w-4 animate-spin", className)} />;
}
