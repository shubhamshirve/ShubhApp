/**
 * PlanCombobox — reusable searchable plan selector
 *
 * Props:
 *   plans       {Array}    list of plan objects (must have .id and .name)
 *   value       {string}   currently selected plan id
 *   onSelect    {fn}       called with plan.id when user picks a plan
 *   displayFn   {fn}       (plan) => string shown in the trigger & list right side
 *                          defaults to showing name only
 *   placeholder {string}   trigger placeholder text (default "Select plan")
 *   disabled    {boolean}
 *   className   {string}   extra classes on the trigger button
 */
import { useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { Button } from "./ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "./ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover";
import { cn } from "../lib/utils";

export function PlanCombobox({
  plans = [],
  value = "",
  onSelect,
  displayFn,
  placeholder = "Select plan",
  disabled = false,
  className = "",
}) {
  const [open, setOpen] = useState(false);

  const selected = plans.find((p) => p.id === value);
  const label = selected
    ? displayFn
      ? displayFn(selected)
      : selected.name
    : null;

  // Sort alphabetically — defensive in case caller didn't sort
  const sorted = [...plans].sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { sensitivity: "base" })
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn(
            "w-full justify-between font-normal text-left h-10 px-3",
            !label && "text-muted-foreground",
            className
          )}
        >
          <span className="truncate">{label ?? placeholder}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>

      <PopoverContent
        className="p-0 w-[var(--radix-popover-trigger-width)]"
        align="start"
      >
        <Command>
          <CommandInput placeholder="Search plan name…" />
          <CommandEmpty>No plans found.</CommandEmpty>
          <CommandGroup className="max-h-64 overflow-y-auto">
            {sorted.map((p) => (
              <CommandItem
                key={p.id}
                value={p.name}
                onSelect={() => {
                  onSelect(p.id);
                  setOpen(false);
                }}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4 shrink-0",
                    value === p.id ? "opacity-100" : "opacity-0"
                  )}
                />
                <span className="flex-1 truncate">{p.name}</span>
                {displayFn && (
                  <span className="ml-2 text-xs text-muted-foreground whitespace-nowrap">
                    {displayFn(p).replace(p.name, "").replace(/^[\s—\-]+/, "")}
                  </span>
                )}
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
