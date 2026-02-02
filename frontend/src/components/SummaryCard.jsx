/**
 * Summary Card Component.
 * Displays a single statistic with icon and label.
 */

export function SummaryCard({ title, value, icon, variant = 'default', subtitle }) {
    const variantClasses = {
        default: 'bg-white border-gray-200',
        success: 'bg-white border-l-4 border-l-emerald-500',
        danger: 'bg-white border-l-4 border-l-red-500',
        warning: 'bg-white border-l-4 border-l-amber-500',
        info: 'bg-white border-l-4 border-l-[#22819A]',
    };

    const valueClasses = {
        default: 'text-gray-900',
        success: 'text-emerald-600',
        danger: 'text-red-600',
        warning: 'text-amber-600',
        info: 'text-[#22819A]',
    };

    const iconBgClasses = {
        default: 'bg-gray-100 text-gray-600',
        success: 'bg-emerald-50 text-emerald-600',
        danger: 'bg-red-50 text-red-600',
        warning: 'bg-amber-50 text-amber-600',
        info: 'bg-[#22819A]/10 text-[#22819A]',
    };

    return (
        <div className={`card p-6 ${variantClasses[variant]}`}>
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                        {title}
                    </p>
                    <p className={`text-4xl font-bold font-outfit ${valueClasses[variant]}`}>
                        {value}
                    </p>
                    {subtitle && (
                        <p className="text-sm text-gray-400 mt-2">{subtitle}</p>
                    )}
                </div>
                {icon && (
                    <div className={`w-14 h-14 rounded-xl flex items-center justify-center text-3xl ${iconBgClasses[variant]}`}>
                        {icon}
                    </div>
                )}
            </div>
        </div>
    );
}

export default SummaryCard;
