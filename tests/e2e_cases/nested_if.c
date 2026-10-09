int main() {
    volatile char a = 60;
    volatile char b = 10;
    volatile char out = 0;

    if (a > 50) {
        if (b < 5) {
            out = 1;
        } else {
            out = 2;
        }
    } else {
        out = 3;
    }
}
