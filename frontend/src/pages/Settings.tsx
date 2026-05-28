import { AppearanceSection } from "@/components/settings/AppearanceSection";
import { CategoriesSection } from "@/components/settings/CategoriesSection";
import { ExportSection } from "@/components/settings/ExportSection";
import { MappingsSection } from "@/components/settings/MappingsSection";
import { PageHeader } from "@/components/layout/PageHeader";

export default function Settings() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Categories, merchant mappings, exports, and appearance."
      />
      <CategoriesSection />
      <MappingsSection />
      <ExportSection />
      <AppearanceSection />
    </div>
  );
}
