import type { VariantProps } from "class-variance-authority"
import { cva } from "class-variance-authority"

export { default as Button } from "./Button.vue"

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/40 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default:
          "border border-blue-500/80 bg-blue-500 text-white shadow-[0_12px_24px_-16px_rgba(59,130,246,0.95)] hover:bg-blue-400",
        destructive:
          "bg-destructive text-white hover:bg-gray-500 focus-visible:ring-destructive/20",
        outline:
          "border border-white/15 bg-gray-900/40 text-gray-100 hover:bg-gray-800/70",
        secondary:
          "border border-white/10 bg-gray-800 text-gray-100 hover:bg-gray-700",
        ghost:
          "text-gray-200 hover:bg-white/5",
        link: "text-white underline-offset-4 hover:underline",
      },
      size: {
        "default": "h-10 px-4 py-2.5 has-[>svg]:px-3",
        "sm": "h-8 gap-1.5 px-3 has-[>svg]:px-2.5",
        "lg": "h-12 px-6 text-base has-[>svg]:px-4",
        "icon": "size-10",
        "icon-sm": "size-9",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)
export type ButtonVariants = VariantProps<typeof buttonVariants>
