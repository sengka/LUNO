"""Listeleme parametreleri için ortak sınırlar (sözleşme 1.6)."""

# Çok büyük sayfa numarası veritabanında taşmaya ve 500 hatasına yol açıyordu (#219, #253).
# limit en fazla 100 olduğu için bu sınır 1.000.000 kayda kadar sayfalamaya yeter.
MAX_PAGE = 10_000
