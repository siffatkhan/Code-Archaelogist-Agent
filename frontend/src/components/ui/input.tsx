import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, invalid, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "focus-ring flex h-9 w-full rounded-md border bg-surface px-3 text-sm text-text-primary placeholder:text-text-muted transition-colors",
          invalid
            ? "border-error/60 focus-visible:outline-error"
            : "border-border hover:border-border-strong",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        aria-invalid={invalid || undefined}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";
