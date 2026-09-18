import { Amplify } from "aws-amplify";

// Values from the deployed backend/template.yaml stack outputs.
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: "ap-south-1_fHTDLLAef",
      userPoolClientId: "12d2kjbeo3fe2k80mqj08j486m",
      region: "ap-south-1",
    },
  },
});
