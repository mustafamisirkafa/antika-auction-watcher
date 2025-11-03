/**
 * Application Routes Configuration
 * Add Seller Preferences route (Phase 14)
 */

export const routes = {
  home: '/',
  dashboard: '/dashboard',
  auctions: '/auctions',
  settings: {
    root: '/settings',
    team: '/settings/team',
    plan: '/settings/plan',
    preferences: '/settings/preferences', // Phase 14
  },
  profit: '/profit',
  admin: '/admin',
} as const;

export const navigationItems = [
  {
    name: 'Dashboard',
    href: routes.dashboard,
    icon: 'HomeIcon',
  },
  {
    name: 'Live Auctions',
    href: routes.auctions,
    icon: 'CurrencyDollarIcon',
  },
  {
    name: 'Profit Advisor',
    href: routes.profit,
    icon: 'ChartBarIcon',
  },
  {
    name: 'Settings',
    icon: 'Cog6ToothIcon',
    children: [
      {
        name: 'Team',
        href: routes.settings.team,
      },
      {
        name: 'Plan & Usage',
        href: routes.settings.plan,
      },
      {
        name: 'Seller Preferences', // Phase 14
        href: routes.settings.preferences,
      },
    ],
  },
  {
    name: 'Admin',
    href: routes.admin,
    icon: 'ShieldCheckIcon',
    adminOnly: true,
  },
];
