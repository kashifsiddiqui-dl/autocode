"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Loader2,
  Mail,
  MoreVertical,
  Plus,
  Shield,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/components/ui/toast";
import { apiClient } from "@/lib/api";
import { getCurrentUser, isAuthenticated } from "@/lib/auth";
import type { User, UserRole } from "@/lib/types";

const roleVariant: Record<UserRole, "default" | "secondary" | "outline"> = {
  admin: "default",
  coder: "secondary",
  viewer: "outline",
};

export default function UsersPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = getCurrentUser();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<UserRole>("coder");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    if (user?.role !== "admin") {
      router.replace("/code");
    }
  }, [router, user?.role]);

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: apiClient.getUsers,
  });

  const createUserMutation = useMutation({
    mutationFn: () =>
      apiClient.createUser({
        email: inviteEmail,
        name: inviteName,
        role: inviteRole,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setInviteOpen(false);
      setInviteEmail("");
      setInviteName("");
      setInviteRole("coder");
      toast({ title: "User invited", description: `${inviteEmail} has been added.`, variant: "success" });
    },
    onError: (error) => {
      toast({ title: "Failed to invite user", description: error.message, variant: "destructive" });
    },
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      apiClient.updateUser(id, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast({ title: "Role updated", variant: "success" });
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast({ title: "User deactivated" });
    },
  });

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-950">
      <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
        <Button
          variant="ghost"
          size="sm"
          className="mb-4 -ml-2"
          onClick={() => router.back()}
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back
        </Button>

        <div className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold text-neutral-900 dark:text-white">
              <Users className="h-6 w-6 text-primary-600" />
              User Management
            </h1>
            <p className="mt-1 text-sm text-neutral-500">
              Manage users and their roles within your organization.
            </p>
          </div>
          <Button onClick={() => setInviteOpen(true)} className="gap-2">
            <UserPlus className="h-4 w-4" />
            Invite User
          </Button>
        </div>

        {/* Users list */}
        <div className="rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 border-b border-neutral-200 px-4 py-3 text-xs font-medium text-neutral-500 dark:border-neutral-800">
            <span>User</span>
            <span>Role</span>
            <span>Last Login</span>
            <span></span>
          </div>

          {isLoading && (
            <div className="space-y-3 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {users?.map((u: User) => (
            <div
              key={u.id}
              className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-4 border-b border-neutral-100 px-4 py-3 last:border-b-0 dark:border-neutral-800"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-neutral-900 dark:text-white">
                  {u.name}
                </p>
                <p className="truncate text-xs text-neutral-500">{u.email}</p>
              </div>
              <Badge variant={roleVariant[u.role]} className="capitalize">
                {u.role}
              </Badge>
              <span className="text-xs text-neutral-400">
                {u.last_login
                  ? formatDistanceToNow(new Date(u.last_login), { addSuffix: true })
                  : "Never"}
              </span>

              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Portal>
                  <DropdownMenu.Content
                    className="z-50 min-w-[160px] rounded-md border bg-white p-1 shadow-md dark:border-neutral-800 dark:bg-neutral-900"
                    sideOffset={5}
                    align="end"
                  >
                    <DropdownMenu.Label className="px-2 py-1 text-xs font-semibold text-neutral-500">
                      Change Role
                    </DropdownMenu.Label>
                    {(["admin", "coder", "viewer"] as UserRole[]).map((role) => (
                      <DropdownMenu.Item
                        key={role}
                        className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-neutral-100 dark:hover:bg-neutral-800 capitalize"
                        onSelect={() => updateRoleMutation.mutate({ id: u.id, role })}
                      >
                        <Shield className="h-3.5 w-3.5" />
                        {role}
                      </DropdownMenu.Item>
                    ))}
                    <DropdownMenu.Separator className="my-1 h-px bg-neutral-200 dark:bg-neutral-700" />
                    <DropdownMenu.Item
                      className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-red-600 outline-none hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
                      onSelect={() => {
                        if (confirm(`Deactivate ${u.name}?`)) {
                          deleteUserMutation.mutate(u.id);
                        }
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Deactivate
                    </DropdownMenu.Item>
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            </div>
          ))}
        </div>

        {/* Invite dialog */}
        <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite User</DialogTitle>
              <DialogDescription>
                Add a new user to your organization. They will receive an email
                invitation.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium">Name</label>
                <Input
                  placeholder="Full name"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Email</label>
                <Input
                  type="email"
                  placeholder="user@organization.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Role</label>
                <Select value={inviteRole} onValueChange={(v) => setInviteRole(v as UserRole)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="coder">Coder</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setInviteOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => createUserMutation.mutate()}
                disabled={
                  !inviteEmail.trim() ||
                  !inviteName.trim() ||
                  createUserMutation.isPending
                }
              >
                {createUserMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Mail className="mr-2 h-4 w-4" />
                )}
                Send Invite
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
