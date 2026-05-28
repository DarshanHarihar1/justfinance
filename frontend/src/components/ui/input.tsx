import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full rounded-[--radius-md] border border-[--color-border-strong] bg-[--color-bg-elevated] px-3 py-2 text-sm",
          "placeholder:text-[--color-text-subtle]",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-[--color-accent]",
          className,
        )}
        {...props}
      />
    );
  },
);
