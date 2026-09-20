import { getApp, getApps, initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const firebaseConfigured = Object.values(firebaseConfig).every(Boolean);

export const firebaseDemoMode = false;

export const firebaseConfigurationError = firebaseConfigured
  ? ""
  : "Firebase Authentication is not configured. Add the required VITE_FIREBASE_* variables.";

const firebaseApp = firebaseConfigured
  ? getApps().length
    ? getApp()
    : initializeApp(firebaseConfig)
  : null;

export const firebaseAuth = firebaseApp ? getAuth(firebaseApp) : null;

export const googleProvider = new GoogleAuthProvider();

export { firebaseConfigured };

export async function getFirebaseIdToken() {
  if (!firebaseAuth) {
    throw new Error("Firebase authentication is not configured.");
  }

  const getCurrentUser = () =>
    firebaseAuth.currentUser;

  let user = getCurrentUser();

  if (!user) {
    user = await new Promise((resolve) => {
      let settled = false;
      const unsubscribe = onAuthStateChanged(
        firebaseAuth,
        (nextUser) => {
          if (settled) return;
          settled = true;
          unsubscribe();
          resolve(nextUser);
        },
        () => {
          if (settled) return;
          settled = true;
          unsubscribe();
          resolve(null);
        }
      );

      window.setTimeout(() => {
        if (settled) return;
        settled = true;
        unsubscribe();
        resolve(getCurrentUser());
      }, 5000);
    });
  }

  if (!user) {
    throw new Error("No authenticated Firebase user.");
  }

  const token = await user.getIdToken();

  if (!token) {
    throw new Error("Unable to obtain Firebase ID token.");
  }

  return token;
}

export { onAuthStateChanged, signInWithPopup, signOut };
