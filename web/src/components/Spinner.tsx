import { BrandMark } from "./Brand";

export function Spinner({ label = "Loading" }: { label?: string }) {
  return <span className="spinner" role="status" aria-label={label} />;
}

export function FullPageSpinner() {
  return (
    <div className="page-loader">
      <BrandMark size={32} />
      <Spinner label="Loading CrewFlow" />
    </div>
  );
}
