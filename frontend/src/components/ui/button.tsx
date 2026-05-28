import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary:
    "bg-[--color-accent] text-white hover:opacity-90 disabled:opacity-50",
  secondary:
    "border border-[--color-border-strong] bg-[--color-bg-elevated] hover:bg-[--color-bg-muted]",
  ghost: "hover:bg-[--color-bg-muted] text-[--color-text-muted]",
  danger: "bg-[--color-danger] text-white hover:opacity-90",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }
>(function Button({ className, variant = "primary", type = "button", ...props }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[--radius-md] px-4 py-2 text-sm font-medium transition-[opacity,background-color] duration-150 ease-out",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[--color-accent]",
        "disabled:pointer-events-none",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
});
