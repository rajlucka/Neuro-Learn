/**
 * src/contexts/UserTypeContext.tsx
 *
 * Tracks the active user type (new / returning / instructor) and the
 * current student ID. Student ID defaults to "S01" for development and
 * will be set from the diagnostic submit response for new students.
 */

import React, { createContext, useContext, useState } from "react";

export type UserType = "new" | "returning" | "instructor";

interface UserTypeContextValue {
  userType:     UserType;
  setUserType:  (t: UserType) => void;
  studentId:    string;
  setStudentId: (id: string) => void;
}

const UserTypeContext = createContext<UserTypeContextValue>({
  userType:     "returning",
  setUserType:  () => {},
  studentId:    "S01",
  setStudentId: () => {},
});

export const useUserType = () => useContext(UserTypeContext);

export const UserTypeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [userType,  setUserType]  = useState<UserType>("returning");
  const [studentId, setStudentId] = useState<string>("S01");

  return (
    <UserTypeContext.Provider value={{ userType, setUserType, studentId, setStudentId }}>
      {children}
    </UserTypeContext.Provider>
  );
};