import * as React from "react";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";

/**
 * Tiny <T k="..."/> wrapper around i18next's t().
 * Renders a span (or chosen element) with `lang` set so the global Punjabi
 * font fallback in globals.css kicks in automatically.
 *
 *   <T k="common.applyNow" />
 *   <T k="web.home.heroTitle" as="h1" className="text-display" />
 *   <T k="mobile.home.feesDueIn" values={{ days: 5 }} />
 */
type AsTag = "span" | "p" | "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "label" | "li" | "div";

interface TProps {
  k: string;
  values?: Record<string, string | number>;
  as?: AsTag;
  className?: string;
}

export function T({ k, values, as: Tag = "span", className }: TProps) {
  const { t, i18n } = useTranslation();
  return (
    <Tag lang={i18n.language} className={className}>
      {t(k, values) as string}
    </Tag>
  );
}

/**
 * Heading that renders the same key in both languages stacked, when both are
 * meaningful (e.g. the `<h1>` on the public Home page). Pa uses Noto Sans
 * Gurmukhi automatically because of the lang="pa" attribute + globals.css.
 */
interface BilingualHeadingProps {
  k: string;
  as?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
  className?: string;
  primaryClassName?: string;
  secondaryClassName?: string;
}

export function BilingualHeading({
  k,
  as: Tag = "h2",
  className,
  primaryClassName,
  secondaryClassName,
}: BilingualHeadingProps) {
  const { i18n } = useTranslation();
  const primary = i18n.language as "en" | "pa";
  const secondary = primary === "en" ? "pa" : "en";
  const primaryText = i18n.getFixedT(primary)(k) as string;
  const secondaryText = i18n.getFixedT(secondary)(k) as string;
  return (
    <Tag className={cn("flex flex-col gap-1", className)}>
      <span lang={primary} className={cn("font-display", primaryClassName)}>
        {primaryText}
      </span>
      <span
        lang={secondary}
        className={cn("text-base font-normal text-muted-foreground", secondaryClassName)}
      >
        {secondaryText}
      </span>
    </Tag>
  );
}

/**
 * Body paragraph that mirrors `BilingualHeading` for long-form copy
 * (e.g. principal's letter, where the en + pa versions both must be shown).
 */
export function BilingualBody({
  k,
  className,
  primaryClassName,
  secondaryClassName,
}: Omit<BilingualHeadingProps, "as">) {
  const { i18n } = useTranslation();
  const primary = i18n.language as "en" | "pa";
  const secondary = primary === "en" ? "pa" : "en";
  const primaryText = i18n.getFixedT(primary)(k) as string;
  const secondaryText = i18n.getFixedT(secondary)(k) as string;
  return (
    <div className={cn("space-y-3", className)}>
      <p lang={primary} className={cn("text-base leading-relaxed", primaryClassName)}>
        {primaryText}
      </p>
      <p
        lang={secondary}
        className={cn("text-base leading-relaxed text-muted-foreground", secondaryClassName)}
      >
        {secondaryText}
      </p>
    </div>
  );
}
