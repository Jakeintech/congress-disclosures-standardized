import React from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { TierBadge, RankBadge, TraderCountBadge, type TierType } from './node-badges';
import { cn } from '@/lib/utils';

// Types
export interface NodeData {
    id: string;
    name: string;
    initials?: string;
    group: 'member' | 'asset' | 'bill' | string;
    party?: 'Democrat' | 'Republican' | 'D' | 'R' | string;
    photo_url?: string;
    logo_url?: string;
    tier?: TierType;
    rank?: number;
    value?: number;
    transaction_count?: number;
    buy_sell_ratio?: number;
    unique_traders?: number;
}

interface NodeComponentProps {
    data: NodeData;
    size?: number;
    className?: string;
}

// Helper functions
const getBorderConfig = (data: NodeData) => {
    if (data.group === 'member') {
        const intensity = Math.min((data.value || 0) / 1000000, 1);
        const baseOpacity = 0.5 + intensity * 0.5;
        const opacityPercent = Math.round(baseOpacity * 100);

        if (data.party === 'Democrat' || data.party === 'D') {
            return {
                borderColor: 'border-blue-500',
                shadow: `shadow-lg shadow-blue-500/${opacityPercent}`
            };
        } else if (data.party === 'Republican' || data.party === 'R') {
            return {
                borderColor: 'border-red-500',
                shadow: `shadow-lg shadow-red-500/${opacityPercent}`
            };
        }
        return { borderColor: 'border-gray-400', shadow: '' };
    }

    if (data.group === 'asset') {
        const ratio = data.buy_sell_ratio || 0;
        if (ratio > 1.5) {
            return { borderColor: 'border-green-500', shadow: 'shadow-lg shadow-green-500/50' };
        } else if (ratio < 0.67) {
            return { borderColor: 'border-red-500', shadow: 'shadow-lg shadow-red-500/50' };
        }
        return { borderColor: 'border-purple-500', shadow: 'shadow-lg shadow-purple-500/50' };
    }

    return { borderColor: 'border-gray-400', shadow: '' };
};

const getFallbackGradient = (data: NodeData) => {
    if (data.group === 'member') {
        if (data.party === 'Democrat' || data.party === 'D') {
            return 'bg-gradient-to-br from-blue-500 to-blue-600 text-white';
        } else if (data.party === 'Republican' || data.party === 'R') {
            return 'bg-gradient-to-br from-red-500 to-red-600 text-white';
        }
        return 'bg-gradient-to-br from-gray-500 to-gray-600 text-white';
    }

    if (data.group === 'asset') {
        return 'bg-gradient-to-br from-purple-500 to-purple-600 text-white font-bold text-lg';
    }

    return 'bg-gray-500 text-white';
};

// Main Component
export const NodeComponent: React.FC<NodeComponentProps> = ({
    data,
    size = 48,
    className
}) => {
    const borderWidth = (data.value || 0) > 500000 ? 4 : 3;
    const { borderColor, shadow } = getBorderConfig(data);
    const fallbackGradient = getFallbackGradient(data);
    const initials = data.initials || data.id?.substring(0, 2).toUpperCase() || '??';

    return (
        <div
            className={cn(
                'relative group flex items-center justify-center',
                className
            )}
            style={{ width: size, height: size }}
        >
            {/* Avatar */}
            <Avatar
                className={cn(
                    'w-full h-full transition-all duration-300',
                    'group-hover:scale-110',
                    borderColor,
                    shadow
                )}
                style={{ borderWidth: `${borderWidth}px` }}
            >
                <AvatarImage
                    src={data.photo_url || data.logo_url}
                    alt={data.name}
                    className="object-cover"
                />
                <AvatarFallback className={fallbackGradient}>
                    {initials}
                </AvatarFallback>
            </Avatar>

            {/* Badges */}
            {data.tier && data.group === 'member' && (
                <TierBadge tier={data.tier} />
            )}

            {data.rank && data.rank <= 10 && (
                <RankBadge rank={data.rank} />
            )}

            {data.group === 'asset' && data.unique_traders && data.unique_traders > 0 && (
                <TraderCountBadge count={data.unique_traders} />
            )}
        </div>
    );
};

// HTML rendering utility for D3 foreignObject
export const renderNodeToHTML = (data: NodeData, size: number = 48): string => {
    const borderWidth = (data.value || 0) > 500000 ? 4 : 3;
    const { borderColor, shadow } = getBorderConfig(data);
    const fallbackGradient = getFallbackGradient(data);
    const initials = data.initials || data.id?.substring(0, 2).toUpperCase() || '??';

    // SVG icon paths
    const tierIcons = {
        platinum: '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15.477 12.89 1.515 8.526a.5.5 0 0 1-.81.47l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 2.686a.5.5 0 0 1-.81-.469l1.514-8.526"/><circle cx="12" cy="8" r="6"/></svg>',
        gold: '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>',
        silver: '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7.21 15 2.66 7.14a2 2 0 0 1 .13-2.2L4.4 2.8A2 2 0 0 1 6 2h12a2 2 0 0 1 1.6.8l1.6 2.14a2 2 0 0 1 .14 2.2L16.79 15"/><path d="M11 12 5.12 2.2"/><path d="m13 12 5.88-9.8"/><path d="M8 7h8"/><circle cx="12" cy="17" r="5"/><path d="M12 18v-2h-.5"/></svg>',
        bronze: '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/></svg>'
    };

    const usersIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>';

    let badgesHTML = '';

    // Tier badge
    if (data.tier && data.group === 'member') {
        const tierColors = {
            platinum: 'bg-gradient-to-br from-slate-400 to-slate-200 text-slate-900',
            gold: 'bg-gradient-to-br from-amber-400 to-amber-200 text-amber-900',
            silver: 'bg-gradient-to-br from-gray-300 to-gray-100 text-gray-900',
            bronze: 'bg-gradient-to-br from-orange-400 to-orange-200 text-orange-900'
        };
        badgesHTML += `
            <div class="absolute -top-1 -right-1 px-1.5 py-1.5 rounded-full ${tierColors[data.tier]} shadow-md flex items-center justify-center">
                ${tierIcons[data.tier]}
            </div>
        `;
    }

    // Rank badge
    if (data.rank && data.rank <= 10) {
        badgesHTML += `
            <div class="absolute -bottom-1 left-1/2 -translate-x-1/2 bg-gradient-to-r from-amber-500 to-amber-600 text-white text-xs px-2 py-0.5 rounded-full font-bold shadow-lg">
                #${data.rank}
            </div>
        `;
    }

    // Unique traders badge
    if (data.group === 'asset' && data.unique_traders && data.unique_traders > 0) {
        badgesHTML += `
            <div class="absolute -bottom-1 left-1/2 -translate-x-1/2 text-xs px-2 py-0.5 rounded-full font-semibold bg-purple-600 text-white shadow-lg flex items-center gap-1">
                ${usersIcon}
                <span>${data.unique_traders}</span>
            </div>
        `;
    }

    return `
        <div class="relative group flex items-center justify-center" style="width: ${size}px; height: ${size}px;">
            <div class="w-full h-full rounded-full overflow-hidden ${borderColor} ${shadow} transition-all duration-300 group-hover:scale-110" style="border-width: ${borderWidth}px;">
                <img
                    src="${data.photo_url || data.logo_url || ''}"
                    alt="${data.name}"
                    class="w-full h-full object-cover"
                    onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
                />
                <div class="w-full h-full ${fallbackGradient} flex items-center justify-center text-xs font-semibold" style="display: none;">
                    ${initials}
                </div>
            </div>
            ${badgesHTML}
        </div>
    `;
};
