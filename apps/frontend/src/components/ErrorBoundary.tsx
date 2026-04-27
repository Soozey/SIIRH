import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo);
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="p-6 bg-red-50 border border-red-200 rounded-xl">
                    <h2 className="text-lg font-bold text-red-700 mb-2">Une erreur d'affichage est survenue</h2>
                    <p className="text-sm text-red-600 mb-4">
                        Le composant n'a pas pu être affiché correctement. Voici les détails techniques :
                    </p>
                    <pre className="bg-white p-4 rounded-lg border border-red-100 text-xs text-red-800 overflow-auto max-h-60">
                        {this.state.error?.toString()}
                        {this.state.error?.stack}
                    </pre>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
