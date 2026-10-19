import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, KeyRound, LogOut } from 'lucide-react';
import { Button, Card, IconButton } from '@/shared/ui';
import { useAuth } from '@/features/auth/AuthContext';
import { AccountsSection } from '@/features/accounts/components/AccountsSection';
import { CategoriesSection } from '@/features/categories/components/CategoriesSection';
import { ProfileSection } from '../components/ProfileSection';
import { PasswordSheet } from '../components/PasswordSheet';

export function SettingsPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [pwd, setPwd] = useState(false);
  const [leaving, setLeaving] = useState(false);

  return (
    <div className="flex flex-col gap-4 px-5 pb-8 pt-5">
      <header className="flex items-center gap-3">
        <IconButton label="Volver" onClick={() => navigate('/')}>
          <ChevronLeft size={20} aria-hidden="true" />
        </IconButton>
        <h1 className="font-display text-[26px] font-bold">Ajustes</h1>
      </header>

      <ProfileSection />
      <AccountsSection />
      <CategoriesSection />

      <Card className="flex flex-col gap-3">
        <h2 className="text-base font-bold">Seguridad</h2>
        <Button variant="secondary" block onClick={() => setPwd(true)}>
          <KeyRound size={16} aria-hidden="true" />
          Cambiar contraseña
        </Button>
        <Button
          variant="secondary"
          block
          className="text-expense"
          loading={leaving}
          onClick={async () => {
            setLeaving(true);
            await logout();
          }}
        >
          <LogOut size={16} aria-hidden="true" />
          Cerrar sesión
        </Button>
      </Card>

      <PasswordSheet open={pwd} onOpenChange={setPwd} />
    </div>
  );
}
