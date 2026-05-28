import { forwardRef, type SelectHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(function Select({ className, children, ...props }, ref) {
  return (
    <select
      ref={ref}
      className={cn(
        "w-full rounded-[--radius-md] border border-[--color-border-strong] bg-[--color-bg-elevated] px-3 py-2 text-sm",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[--color-accent]",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
});
