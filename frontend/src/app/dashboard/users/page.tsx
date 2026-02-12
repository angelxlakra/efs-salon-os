'use client';

import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from '@/components/ui/button';
import { Plus, Loader2, Search, User, UserCog, KeyRound, Edit2, CheckCircle2, Mail, Phone } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useAuthStore } from '@/stores/auth-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { UserDialog } from '@/components/users/user-dialog';
import { StaffDialog } from '@/components/users/staff-dialog';
import { ResetPasswordDialog } from '@/components/users/reset-password-dialog';

export default function UsersPage() {
  const { user } = useAuthStore();
  const isOwner = user?.role === 'owner';

  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState<any[]>([]);
  const [staff, setStaff] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Dialog states
  const [userDialog, setUserDialog] = useState<{ open: boolean; user: any | null }>(
    { open: false, user: null }
  );
  const [staffDialog, setStaffDialog] = useState<{ open: boolean; staff: any | null }>(
    { open: false, staff: null }
  );
  const [passwordDialog, setPasswordDialog] = useState<{ open: boolean; user: any | null }>(
    { open: false, user: null }
  );

  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      if (activeTab === 'users') {
        const { data } = await apiClient.get('/users');
        setUsers(data.items || []);
      } else {
        const { data } = await apiClient.get('/staff');
        setStaff(data.items || []);
      }
    } catch (error: any) {
      toast.error('Failed to load data');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!hasMounted) {
    return null;
  }

  const filteredData = (activeTab === 'users' ? users : staff).filter((item) => {
    const query = searchQuery.toLowerCase();
    if (activeTab === 'users') {
      return (
        item.full_name.toLowerCase().includes(query) ||
        item.username.toLowerCase().includes(query) ||
        item.email?.toLowerCase().includes(query)
      );
    } else {
      return (
        item.display_name.toLowerCase().includes(query) ||
        item.user?.username.toLowerCase().includes(query)
      );
    }
  });

  const getInitials = (name: string) => {
    return (name || '')
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Users & Staff</h1>
          <p className="text-muted-foreground mt-1">
            Manage system access, permissions, and staff profiles.
          </p>
        </div>
        <div className="flex gap-2">
            {activeTab === 'users' && isOwner && (
            <Button onClick={() => setUserDialog({ open: true, user: null })} className="shadow-sm">
                <Plus className="h-4 w-4 mr-2" />
                Add User
            </Button>
            )}
            {activeTab === 'staff' && (isOwner || user?.role === 'receptionist') && (
            <Button onClick={() => setStaffDialog({ open: true, staff: null })} className="shadow-sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Staff
            </Button>
            )}
        </div>
      </div>

      {/* Metrics Section - Simulated for now as we might not have all endpoints */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="shadow-sm border-none bg-gradient-to-br from-white to-gray-50/50">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
                <UserCog className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">System Users</p>
                <h3 className="text-2xl font-bold text-gray-900">{users.length}</h3>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-none bg-gradient-to-br from-white to-gray-50/50">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-50 text-purple-600 rounded-lg">
                <User className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Staff Profiles</p>
                <h3 className="text-2xl font-bold text-gray-900">{staff.length}</h3>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-sm border-none bg-gradient-to-br from-white to-gray-50/50">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-50 text-green-600 rounded-lg">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">Active Users</p>
                <h3 className="text-2xl font-bold text-gray-900">
                  {users.filter(u => u.is_active).length}
                </h3>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="users" value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <TabsList className="bg-muted/50 p-1 h-11 w-fit">
            <TabsTrigger value="users" className="h-9 px-4 text-sm">
                <UserCog className="h-4 w-4 mr-2" />
                System Users
            </TabsTrigger>
            <TabsTrigger value="staff" className="h-9 px-4 text-sm">
                <User className="h-4 w-4 mr-2" />
                Staff Profiles
            </TabsTrigger>
            </TabsList>

            <div className="relative w-full sm:w-72">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                placeholder={activeTab === 'users' ? "Search users..." : "Search staff..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-white"
                />
            </div>
        </div>

        <TabsContent value="users" className="mt-0">
            <Card className="border shadow-sm overflow-hidden">
                <CardContent className="p-0">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center h-64 gap-4">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        <p className="text-sm text-muted-foreground">Loading users...</p>
                    </div>
                ) : filteredData.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
                        <div className="bg-muted/50 p-4 rounded-full mb-4">
                            <UserCog className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900">No users found</h3>
                        <p className="text-muted-foreground max-w-sm mt-2">
                            {searchQuery ? `No users matching "${searchQuery}"` : "Get started by adding a new system user."}
                        </p>
                        {!searchQuery && isOwner && (
                            <Button variant="outline" className="mt-6" onClick={() => setUserDialog({ open: true, user: null })}>
                                <Plus className="h-4 w-4 mr-2" />
                                Add First User
                            </Button>
                        )}
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50/50 border-b">
                                <tr>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">User</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Role</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Contact</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                                    {isOwner && <th className="px-6 py-4 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 bg-white">
                                {filteredData.map((u) => (
                                    <tr key={u.id} className="hover:bg-gray-50/60 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <Avatar className="h-9 w-9 border border-gray-200">
                                                    <AvatarFallback className="bg-primary/5 text-primary text-xs font-medium">
                                                        {getInitials(u.full_name)}
                                                    </AvatarFallback>
                                                </Avatar>
                                                <div>
                                                    <div className="font-medium text-gray-900">{u.full_name}</div>
                                                    <div className="text-xs text-muted-foreground">@{u.username}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Badge variant="outline" className="capitalize font-normal">
                                                {u.role?.name?.toLowerCase().replace('_', ' ')}
                                            </Badge>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="space-y-1">
                                                <div className="text-sm text-gray-700 flex items-center gap-2">
                                                    <Mail className="h-3 w-3 text-gray-400" />
                                                    {u.email || '-'}
                                                </div>
                                                <div className="text-sm text-gray-700 flex items-center gap-2">
                                                    <Phone className="h-3 w-3 text-gray-400" />
                                                    {u.phone}
                                                </div>
                                            </div>
                                        </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                            <Badge 
                                                variant={u.is_active ? 'default' : 'destructive'} 
                                                className={`font-normal ${u.is_active ? 'bg-green-50 text-green-700 hover:bg-green-100 hover:text-green-800 border-green-200' : ''}`}
                                            >
                                                {u.is_active ? 'Active' : 'Inactive'}
                                            </Badge>
                                        </td>
                                        {isOwner && (
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                                                <div className="flex justify-end gap-1">
                                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-blue-600" onClick={() => setUserDialog({ open: true, user: u })}>
                                                        <Edit2 className="h-4 w-4" />
                                                    </Button>
                                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-orange-600" onClick={() => setPasswordDialog({ open: true, user: u })}>
                                                        <KeyRound className="h-4 w-4" />
                                                    </Button>
                                                </div>
                                            </td>
                                        )}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                </CardContent>
            </Card>
        </TabsContent>

        <TabsContent value="staff" className="mt-0">
            <Card className="border shadow-sm overflow-hidden">
                <CardContent className="p-0">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center h-64 gap-4">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        <p className="text-sm text-muted-foreground">Loading staff...</p>
                    </div>
                ) : filteredData.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
                        <div className="bg-muted/50 p-4 rounded-full mb-4">
                            <User className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900">No staff profiles found</h3>
                        <p className="text-muted-foreground max-w-sm mt-2">
                             {searchQuery ? `No staff matching "${searchQuery}"` : "Create staff profiles to assign services and appointments."}
                        </p>
                        {!searchQuery && (isOwner || user?.role === 'receptionist') && (
                            <Button variant="outline" className="mt-6" onClick={() => setStaffDialog({ open: true, staff: null })}>
                                <Plus className="h-4 w-4 mr-2" />
                                Add First Staff
                            </Button>
                        )}
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50/50 border-b">
                                <tr>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Staff Member</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Linked Account</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Specialization</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Expected Cash</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Type</th>
                                    <th className="px-6 py-4 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
                                    {(isOwner || user?.role === 'receptionist') && <th className="px-6 py-4 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 bg-white">
                                {filteredData.map((s) => (
                                    <tr key={s.id} className="hover:bg-gray-50/60 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                             <div className="flex items-center gap-3">
                                                <Avatar className="h-9 w-9 border border-gray-200">
                                                    <AvatarFallback className="bg-purple-50 text-purple-600 text-xs font-medium">
                                                        {getInitials(s.display_name)}
                                                    </AvatarFallback>
                                                </Avatar>
                                                <div>
                                                    <div className="font-medium text-gray-900">{s.display_name}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {s.user ? (
                                                <div className="flex items-center gap-1.5">
                                                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                                                    @{s.user.username}
                                                </div>
                                            ) : (
                                                <span className="text-gray-400 italic">No account linked</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex flex-wrap gap-1 max-w-[200px]">
                                                {s.specialization && s.specialization.length > 0 ? (
                                                    s.specialization.slice(0, 2).map((spec: string, i: number) => (
                                                        <Badge key={i} variant="secondary" className="text-xs font-normal border-gray-200">
                                                            {spec}
                                                        </Badge>
                                                    ))
                                                ) : (
                                                    <span className="text-gray-400 text-sm">-</span>
                                                )}
                                                {s.specialization && s.specialization.length > 2 && (
                                                    <Badge variant="outline" className="text-xs text-gray-500">+{s.specialization.length - 2}</Badge>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-700">
                                            ₹{((s.current_drawer_balance || 0) / 100).toFixed(2)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Badge
                                                variant="outline"
                                                className={`font-normal ${s.is_service_provider ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-gray-50 text-gray-500 border-gray-200'}`}
                                            >
                                                {s.is_service_provider ? 'Service Provider' : 'Non-Provider'}
                                            </Badge>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Badge
                                                variant={s.is_active ? 'default' : 'destructive'}
                                                className={`font-normal ${s.is_active ? 'bg-green-50 text-green-700 hover:bg-green-100 hover:text-green-800 border-green-200' : ''}`}
                                            >
                                                {s.is_active ? 'Active' : 'Inactive'}
                                            </Badge>
                                        </td>
                                        {(isOwner || user?.role === 'receptionist') && (
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-blue-600" onClick={() => setStaffDialog({ open: true, staff: s })}>
                                                    <Edit2 className="h-4 w-4" />
                                                </Button>
                                            </td>
                                        )}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                </CardContent>
            </Card>
        </TabsContent>
      </Tabs>


      <UserDialog 
        open={userDialog.open} 
        user={userDialog.user} 
        onClose={() => setUserDialog({ open: false, user: null })}
        onSuccess={() => {
            fetchData();
            setUserDialog({ open: false, user: null });
        }}
      />

      <StaffDialog 
        open={staffDialog.open} 
        staff={staffDialog.staff} 
        onClose={() => setStaffDialog({ open: false, staff: null })}
        onSuccess={() => {
            fetchData();
            setStaffDialog({ open: false, staff: null });
        }}
      />

      <ResetPasswordDialog 
        open={passwordDialog.open} 
        user={passwordDialog.user} 
        onClose={() => setPasswordDialog({ open: false, user: null })}
        onSuccess={() => {
            setPasswordDialog({ open: false, user: null });
        }}
      />
    </div>
  );
}
