import './globals.css';
export const metadata = {
  title: 'WARBREAK',
  description: 'Every wargame shows what happens. WARBREAK shows why it was always going to happen.',
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
