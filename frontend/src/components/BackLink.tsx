import { Link } from "react-router-dom";

type Props = {
  label?: string;
  to: string;
};

export function BackLink({ label = "Back", to }: Props) {
  return (
    <nav aria-label="Back" className="text-sm font-medium text-zinc-600">
      <Link className="inline-flex hover:text-teal-700" to={to}>
        {label}
      </Link>
    </nav>
  );
}
