import { Component, type ErrorInfo, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  /** Clears the error when it changes (the app passes the path, so moving to another page recovers). */
  resetKey?: string;
}

interface State {
  error: Error | null;
}

/**
 * Catches a render error anywhere below it. Without one, React unmounts the
 * whole app on any render error and leaves a blank page.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Render error", error, info.componentStack);
  }

  componentDidUpdate(prev: Props) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  render() {
    return this.state.error ? <ErrorFallback error={this.state.error} /> : this.props.children;
  }
}

function ErrorFallback({ error }: { error: Error }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <div role="alert" className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="max-w-md w-full rounded-md border border-red-300 bg-red-50 p-5 text-sm space-y-3">
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-5 w-5 text-red-700 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <p className="font-semibold text-red-900">
              {t("portal.common.crashTitle", "Something went wrong on this page.")}
            </p>
            <p className="text-red-900/80">
              {t("portal.common.crashHint", "Reload the page to carry on. Changes that weren't saved may need to be entered again.")}
            </p>
            {error.message && <p className="text-xs text-muted-foreground break-words">{error.message}</p>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2 justify-end">
          <Button variant="outline" onClick={() => navigate("/dashboard")}>
            {t("portal.common.goDashboard", "Go to the dashboard")}
          </Button>
          <Button onClick={() => window.location.reload()}>
            <RefreshCw className="h-4 w-4" /> {t("portal.common.reloadPage", "Reload the page")}
          </Button>
        </div>
      </div>
    </div>
  );
}
