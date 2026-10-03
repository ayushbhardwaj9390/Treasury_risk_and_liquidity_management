import "./styles.css";

export const metadata = {
  title: "Global Treasury AI",
  description: "Treasury risk and liquidity intelligence for multinational enterprises",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
