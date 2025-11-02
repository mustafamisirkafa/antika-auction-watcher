/**
 * Team Settings Page
 * Manage team members and roles
 */
import React, { useEffect, useState } from 'react';
import { useTeamStore, TeamMember } from '@/store/teamStore';

export default function TeamSettings() {
  const { currentTeam, loading, error } = useTeamStore();
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [addMemberEmail, setAddMemberEmail] = useState('');
  const [addMemberRole, setAddMemberRole] = useState<'ANALYST' | 'VIEWER'>('VIEWER');
  const [showAddForm, setShowAddForm] = useState(false);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';

  useEffect(() => {
    if (currentTeam) {
      fetchMembers();
    }
  }, [currentTeam]);

  const fetchMembers = async () => {
    if (!currentTeam) return;

    setLoadingMembers(true);
    try {
      const response = await fetch(`${API_BASE_URL}/teams/${currentTeam.id}/members`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Team-Id': currentTeam.id.toString(),
        },
      });

      if (!response.ok) throw new Error('Failed to fetch members');

      const data = await response.json();
      setMembers(data);
    } catch (error) {
      console.error('Failed to fetch members:', error);
    } finally {
      setLoadingMembers(false);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentTeam) return;

    // In a real app, you'd search for user by email first to get their ID
    // For now, this is a placeholder
    alert('Add member functionality requires user ID lookup. This would be implemented with a user search endpoint.');
  };

  const handleChangeRole = async (userId: number, newRole: string) => {
    if (!currentTeam) return;

    try {
      const response = await fetch(`${API_BASE_URL}/teams/${currentTeam.id}/members/${userId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Team-Id': currentTeam.id.toString(),
        },
        body: JSON.stringify({ role: newRole }),
      });

      if (!response.ok) throw new Error('Failed to update role');

      await fetchMembers();
    } catch (error) {
      console.error('Failed to update role:', error);
      alert('Failed to update member role');
    }
  };

  const handleRemoveMember = async (userId: number) => {
    if (!currentTeam) return;

    if (!confirm('Are you sure you want to remove this member?')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/teams/${currentTeam.id}/members/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'X-Team-Id': currentTeam.id.toString(),
        },
      });

      if (!response.ok) throw new Error('Failed to remove member');

      await fetchMembers();
    } catch (error) {
      console.error('Failed to remove member:', error);
      alert('Failed to remove member');
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'OWNER':
        return 'bg-purple-100 text-purple-800';
      case 'ADMIN':
        return 'bg-blue-100 text-blue-800';
      case 'ANALYST':
        return 'bg-green-100 text-green-800';
      case 'VIEWER':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (!currentTeam) {
    return (
      <div className="p-6">
        <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 p-4 rounded-lg">
          ?? No team selected. Please select a team first.
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Team Settings</h1>
        <p className="text-gray-600 mt-1">Manage your team members and their roles</p>
      </div>

      {/* Team Info */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Team Information</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-gray-600">Team Name</label>
            <p className="text-lg font-medium">{currentTeam.name}</p>
          </div>
          <div>
            <label className="text-sm text-gray-600">Plan</label>
            <p className="text-lg font-medium">{currentTeam.plan_code}</p>
          </div>
        </div>
      </div>

      {/* Members List */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Team Members ({members.length})</h2>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {showAddForm ? 'Cancel' : '+ Add Member'}
          </button>
        </div>

        {/* Add Member Form */}
        {showAddForm && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <form onSubmit={handleAddMember} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={addMemberEmail}
                  onChange={(e) => setAddMemberEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="user@example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role
                </label>
                <select
                  value={addMemberRole}
                  onChange={(e) => setAddMemberRole(e.target.value as any)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="VIEWER">Viewer - Read-only access</option>
                  <option value="ANALYST">Analyst - Can manage agents</option>
                </select>
              </div>
              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
              >
                Send Invitation
              </button>
            </form>
          </div>
        )}

        {loadingMembers ? (
          <div className="text-center py-8 text-gray-500">Loading members...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                    Email
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                    Role
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">
                    Joined
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-gray-700">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="flex items-center">
                        <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white font-semibold mr-3">
                          {member.user_email.charAt(0).toUpperCase()}
                        </div>
                        <span className="font-medium">{member.user_email}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {member.role === 'OWNER' ? (
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getRoleColor(member.role)}`}>
                          {member.role}
                        </span>
                      ) : (
                        <select
                          value={member.role}
                          onChange={(e) => handleChangeRole(member.user_id, e.target.value)}
                          className={`px-3 py-1 rounded-full text-sm font-medium ${getRoleColor(member.role)} border-none outline-none cursor-pointer`}
                        >
                          <option value="ADMIN">ADMIN</option>
                          <option value="ANALYST">ANALYST</option>
                          <option value="VIEWER">VIEWER</option>
                        </select>
                      )}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {new Date(member.joined_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {member.role !== 'OWNER' && (
                        <button
                          onClick={() => handleRemoveMember(member.user_id)}
                          className="text-red-600 hover:text-red-800 text-sm font-medium"
                        >
                          Remove
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Role Descriptions */}
      <div className="bg-gray-50 rounded-lg p-6 mt-6">
        <h3 className="font-semibold mb-3">Role Descriptions</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-start">
            <span className="inline-block px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs font-medium mr-3">
              OWNER
            </span>
            <span className="text-gray-700">
              Full control over team, billing, and can delete team
            </span>
          </div>
          <div className="flex items-start">
            <span className="inline-block px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium mr-3">
              ADMIN
            </span>
            <span className="text-gray-700">
              Can manage members, agents, and settings (except billing)
            </span>
          </div>
          <div className="flex items-start">
            <span className="inline-block px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-medium mr-3">
              ANALYST
            </span>
            <span className="text-gray-700">
              Can view agents, create reports, and limited agent control
            </span>
          </div>
          <div className="flex items-start">
            <span className="inline-block px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs font-medium mr-3">
              VIEWER
            </span>
            <span className="text-gray-700">Read-only access to team data</span>
          </div>
        </div>
      </div>
    </div>
  );
}
