"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ChevronDown,
  Code2,
  FolderTree,
  History,
  LogOut,
  Settings,
  Shield,
  User,
  Users,
} from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Avatar from "@radix-ui/react-avatar";
import { cn } from "@/lib/utils";
import { getCurrentUser, logout } from "@/lib/auth";

const navLinks = [
  { href: "/code", label: "Code", icon: Code2 },
  { href: "/sessions", label: "Sessions", icon: History },
  { href: "/browse", label: "Browse", icon: FolderTree },
];

export function Navbar() {
  const pathname = usePathname();
  const user = getCurrentUser();

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "AC";

  return (
    <header className="sticky top-0 z-40 border-b bg-white dark:bg-neutral-950">
      <div className="flex h-14 items-center px-4 lg:px-6">
        {/* Logo */}
        <Link href="/code" className="flex items-center gap-2 mr-8">
          <Activity className="h-6 w-6 text-primary-600" />
          <span className="text-lg font-bold text-neutral-900 dark:text-white">
            Auto Code
          </span>
        </Link>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300"
                    : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 dark:text-neutral-400 dark:hover:bg-neutral-800 dark:hover:text-white",
                )}
              >
                <Icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* User menu */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-ring">
              <Avatar.Root className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900">
                <Avatar.Fallback className="text-xs font-medium text-primary-700 dark:text-primary-300">
                  {initials}
                </Avatar.Fallback>
              </Avatar.Root>
              <div className="hidden text-left md:block">
                <p className="text-sm font-medium text-neutral-900 dark:text-white">
                  {user?.name || "User"}
                </p>
                <p className="text-xs text-neutral-500">{user?.role || "coder"}</p>
              </div>
              <ChevronDown className="h-4 w-4 text-neutral-400" />
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              className="z-50 min-w-[200px] rounded-md border bg-white p-1 shadow-md dark:border-neutral-800 dark:bg-neutral-900"
              sideOffset={5}
              align="end"
            >
              <div className="px-2 py-1.5 text-sm">
                <p className="font-medium text-neutral-900 dark:text-white">
                  {user?.name}
                </p>
                <p className="text-xs text-neutral-500">{user?.email}</p>
              </div>
              <DropdownMenu.Separator className="my-1 h-px bg-neutral-200 dark:bg-neutral-700" />

              <DropdownMenu.Item asChild>
                <Link
                  href="/settings"
                  className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-neutral-700 outline-none hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
                >
                  <Settings className="h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenu.Item>

              {user?.role === "admin" && (
                <DropdownMenu.Item asChild>
                  <Link
                    href="/users"
                    className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-neutral-700 outline-none hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-800"
                  >
                    <Users className="h-4 w-4" />
                    User Management
                  </Link>
                </DropdownMenu.Item>
              )}

              <DropdownMenu.Separator className="my-1 h-px bg-neutral-200 dark:bg-neutral-700" />

              <DropdownMenu.Item
                className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-red-600 outline-none hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
                onSelect={() => logout()}
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  );
}
