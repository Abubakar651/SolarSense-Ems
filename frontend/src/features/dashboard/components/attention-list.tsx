import Link from 'next/link';
import { IconChip } from '@/components/ui/icon-chip';
import type { AttentionItem } from '../attention';

export function AttentionList({ items }: { items: AttentionItem[] }) {
  return (
    <ul className="list">
      {items.map(({ icon, tone, title, detail, link }) => (
        <li key={title}>
          <IconChip icon={icon} tone={tone} />
          <div>
            <b>{title}</b>
            <p className="small muted">
              {detail} {link && <Link href={link.href}>{link.label}</Link>}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}
