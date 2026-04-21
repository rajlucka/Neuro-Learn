import { useUserType } from "@/contexts/UserTypeContext";
import { NewStudentView } from "@/components/views/NewStudentView";
import { ReturningStudentView } from "@/components/views/ReturningStudentView";
import { InstructorView } from "@/components/views/InstructorView";

const Index = () => {
  const { userType } = useUserType();

  if (userType === "new") return <NewStudentView />;
  if (userType === "instructor") return <InstructorView />;
  return <ReturningStudentView />;
};

export default Index;
