import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { Toaster } from "sonner";

import { queryClient } from "@/lib/query";
import { router } from "@/routes";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <Toaster position="top-center" richColors closeButton />
    </QueryClientProvider>
  );
}
