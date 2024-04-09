namespace ForgeCouple {
    export class Subject<T> {
        private listeners: ((arg: T) => void)[] = [];

        public subscribe(listener: (arg: T) => void): void {
            this.listeners.push(listener);
        }

        public unsubscribe(listener: (arg: T) => void): void {
            let index = this.listeners.indexOf(listener);
            if (index >= 0)
                this.listeners.splice(index, 1);
        }

        public next(arg: T): void {
            for (let listener of this.listeners) {
                listener(arg);
            }
        }
    }
}
