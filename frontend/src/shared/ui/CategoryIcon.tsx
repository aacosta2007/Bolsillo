import {
  Archive, Baby, Banknote, Beer, Bike, Book, Briefcase, Building2, Bus, Camera, Car, Clapperboard, Coffee, Coins,
  CircleEllipsis, CirclePlus, CreditCard, Dog, Dumbbell, Flag, Fuel, Gamepad2, Gem, Gift, GraduationCap, HandCoins,
  Heart, HeartPulse, House, Landmark, Laptop, Music, Pill, PiggyBank, Plane, Receipt, Repeat, Scissors,
  Shirt, ShoppingBag, ShoppingCart, Smartphone, Sparkles, Star, Stethoscope, Tag, Target, Ticket, TrainFront,
  TrendingUp, Tv, Umbrella, Utensils, Wallet, Wifi, Wrench, Zap, type LucideIcon,
} from 'lucide-react';

/** Iconos lucide soportados (nombre kebab-case que guarda el backend → componente). */
export const ICONS: Record<string, LucideIcon> = {
  utensils: Utensils,
  bus: Bus,
  home: House,
  house: House,
  zap: Zap,
  'heart-pulse': HeartPulse,
  clapperboard: Clapperboard,
  'shopping-bag': ShoppingBag,
  'graduation-cap': GraduationCap,
  repeat: Repeat,
  'circle-ellipsis': CircleEllipsis,
  briefcase: Briefcase,
  laptop: Laptop,
  'trending-up': TrendingUp,
  gift: Gift,
  'plus-circle': CirclePlus,
  'circle-plus': CirclePlus,
  landmark: Landmark,
  wallet: Wallet,
  banknote: Banknote,
  'credit-card': CreditCard,
  'piggy-bank': PiggyBank,
  plane: Plane,
  car: Car,
  coffee: Coffee,
  shirt: Shirt,
  'gamepad-2': Gamepad2,
  music: Music,
  book: Book,
  baby: Baby,
  dog: Dog,
  dumbbell: Dumbbell,
  fuel: Fuel,
  smartphone: Smartphone,
  wifi: Wifi,
  tv: Tv,
  stethoscope: Stethoscope,
  pill: Pill,
  wrench: Wrench,
  tag: Tag,
  star: Star,
  heart: Heart,
  sparkles: Sparkles,
  'building-2': Building2,
  bike: Bike,
  'train-front': TrainFront,
  'shopping-cart': ShoppingCart,
  receipt: Receipt,
  'hand-coins': HandCoins,
  coins: Coins,
  target: Target,
  flag: Flag,
  gem: Gem,
  umbrella: Umbrella,
  scissors: Scissors,
  beer: Beer,
  ticket: Ticket,
  camera: Camera,
  archive: Archive,
};

export const ICON_NAMES = Object.keys(ICONS).filter((n) => n !== 'house' && n !== 'circle-plus');

export function CategoryIcon({ name, size = 18, className }: { name?: string | null; size?: number; className?: string }) {
  const Icon = (name && ICONS[name]) || CircleEllipsis;
  return <Icon size={size} className={className} aria-hidden="true" />;
}

/** Cuadro con color + icono (avatar de categoría/cuenta/meta). */
export function IconBadge({
  icon,
  color,
  size = 40,
  rounded = 12,
}: {
  icon?: string | null;
  color?: string | null;
  size?: number;
  rounded?: number;
}) {
  const c = color || '#55615B';
  return (
    <span
      aria-hidden="true"
      className="flex shrink-0 items-center justify-center text-white"
      style={{ width: size, height: size, borderRadius: rounded, background: c }}
    >
      <CategoryIcon name={icon} size={Math.round(size * 0.46)} />
    </span>
  );
}
