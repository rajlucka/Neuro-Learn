import { useUserType, UserType } from "@/contexts/UserTypeContext";
import { User, UserCheck, GraduationCap } from "lucide-react";

const types: { value: UserType; label: string; icon: React.ElementType }[] = [
  { value: "new", label: "New Student", icon: User },
  { value: "returning", label: "Returning", icon: UserCheck },
  { value: "instructor", label: "Instructor", icon: GraduationCap },
];

export function UserTypeSwitcher() {
  const { userType, setUserType } = useUserType();
  return (
    <div className="flex items-center gap-1 rounded-lg bg-secondary p-1">
      {types.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          onClick={() => setUserType(value)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
            userType === value
              ? "bg-card text-foreground shadow-glass"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Icon className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </div>
  );
}
