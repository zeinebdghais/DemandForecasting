namespace DemandForecastingA.Models
{
    public class Prediction
    {
    //    public string ds { get; set; }
    //    public double Prophet_Pred { get; set; }
    //    public double RF_Pred { get; set; }
    //    public double Avg_Pred { get; set; }
    //}
        public string ds { get; set; }             // Date
        public double Prophet_Pred { get; set; }   // Prédiction Prophet
        public double RF_Correction { get; set; }  // Correction RandomForest
        public double Final_Hybrid { get; set; }   // Résultat final

        public int HybridAsInt => (int)Math.Round(Final_Hybrid);

    }
}
