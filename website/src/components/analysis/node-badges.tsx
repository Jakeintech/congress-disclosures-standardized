import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Award, Trophy, Medal, Shield, Users } from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
export type TierType = 'platinum' | 'gold' | 'silver' | 'bronze';

interface TierBadgeProps {
    tier: TierType;
    className?: string;
}

interface RankBadgeProps {
    rank: number;
    className?: string;
}

interface TraderCountBadgeProps {
    count: number;
    className?: string;
}

// Tier Badge Component
export const TierBadge: React.FC<TierBadgeProps> = ({ tier, className }) => {
    const getTierConfig = (tier: TierType) => {
        const configs = {
            platinum: {
                Icon: Award,
                gradient: 'from-slate-400 to-slate-200',
                textColor: 'text-slate-900',
                label: 'Platinum Tier'
            },
            gold: {
                Icon: Trophy,
                gradient: 'from-amber-400 to-amber-200',
                textColor: 'text-amber-900',
                label: 'Gold Tier'
            },
            silver: {
                Icon: Medal,
                gradient: 'from-gray-300 to-gray-100',
                textColor: 'text-gray-900',
                label: 'Silver Tier'
            },
            bronze: {
                Icon: Shield,
                gradient: 'from-orange-400 to-orange-200',
                textColor: 'text-orange-900',
                label: 'Bronze Tier'
            }
        };
        return configs[tier];
    };

    const config = getTierConfig(tier);
    const { Icon, gradient, textColor, label } = config;

    return (
        <Badge
            className={cn(
                'absolute -top-1 -right-1 p-1.5 transition-transform hover:scale-110',
                `bg-gradient-to-br ${gradient} ${textColor}`,
                'shadow-md border-0',
                className
            )}
            title={label}
        >
            <Icon className="w-3 h-3" />
        </Badge>
    );
};

// Rank Badge Component
export const RankBadge: React.FC<RankBadgeProps> = ({ rank, className }) => {
    return (
        <Badge
            className={cn(
                'absolute -bottom-1 left-1/2 -translate-x-1/2',
                'bg-gradient-to-r from-amber-500 to-amber-600',
                'text-white text-xs px-2 py-0.5 font-bold shadow-lg',
                'border-0',
                className
            )}
            title={`Rank #${rank}`}
        >
            #{rank}
        </Badge>
    );
};

// Trader Count Badge Component
export const TraderCountBadge: React.FC<TraderCountBadgeProps> = ({ count, className }) => {
    return (
        <Badge
            variant="secondary"
            className={cn(
                'absolute -bottom-1 left-1/2 -translate-x-1/2',
                'bg-purple-600 text-white text-xs px-2 py-0.5 font-semibold',
                'shadow-lg border-0 flex items-center gap-1',
                className
            )}
            title={`${count} unique ${count === 1 ? 'trader' : 'traders'}`}
        >
            <Users className="w-3 h-3" />
            <span>{count}</span>
        </Badge>
    );
};
